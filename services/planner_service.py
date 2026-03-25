import json
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Any

from api.schemas import ItineraryRequest
from search.semantic_search import semantic_search
from services.llm_service import generate_text


CATEGORY_DURATION = {
    "museum": 120,
    "gallery": 90,
    "zoo": 180,
    "park": 75,
    "nature_reserve": 90,
    "beach": 120,
    "historic_site": 75,
    "shopping": 90,
    "botanical_garden": 120,
    "aquarium": 150,
    "restaurant": 75,
    "nightlife": 120,
    "attraction": 90,
}

CATEGORY_TIME_TAGS = {
    "museum": ["morning", "afternoon"],
    "gallery": ["morning", "afternoon"],
    "zoo": ["morning"],
    "park": ["morning", "evening"],
    "nature_reserve": ["morning", "evening"],
    "beach": ["morning", "evening"],
    "historic_site": ["morning", "afternoon"],
    "shopping": ["afternoon", "evening"],
    "restaurant": ["afternoon", "evening"],
    "nightlife": ["evening"],
    "attraction": ["morning", "afternoon", "evening"],
}

DEFAULT_DURATION = 90

PACE_LIMITS = {
    "relaxed": 240,   # 4 hours/day
    "balanced": 360,  # 6 hours/day
    "packed": 480,    # 8 hours/day
}

PACE_TO_MAX_CANDIDATES = {
    "relaxed": 5,
    "balanced": 7,
    "packed": 9,
}

PACE_TO_STOPS_PER_DAY = {
    "relaxed": 2,
    "balanced": 2,
    "packed": 3,
}

TIME_BLOCK_ORDER = {
    "morning": 1,
    "afternoon": 2,
    "evening": 3,
}

MIN_ITINERARY_SCORE = 0.40

SLOTS = ["morning", "afternoon", "evening"]

WATERFRONT_QUERY_TERMS = [
    "waterfront",
    "river",
    "beach",
    "bay",
    "harbor",
    "harbour",
    "riverwalk",
    "marina",
    "pier",
]

# Use strong destination-style waterfront terms only.
WATERFRONT_STRONG_TERMS = [
    "waterfront",
    "riverwalk",
    "river walk",
    "riverfront",
    "bayfront",
    "harbor",
    "harbour",
    "beach",
    "marina",
    "pier",
    "boardwalk",
    "shore",
]

ANCHOR_TERMS = [
    "riverwalk",
    "river walk",
    "bayfront",
    "waterfront",
    "harbor",
    "harbour",
    "beach",
    "marina",
    "pier",
    "boardwalk",
    "shore",
    "riverfront",
]


def assign_slot(place: dict, used_slots: set[str]) -> str:
    for tag in place.get("time_of_day_tags", ["afternoon"]):
        if tag not in used_slots:
            return tag
    for slot in SLOTS:
        if slot not in used_slots:
            return slot
    return "afternoon"


def haversine(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return float("inf")

    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def order_by_proximity(places: list[dict]) -> list[dict]:
    if not places:
        return []

    ordered = [places[0]]
    remaining = places[1:]

    while remaining:
        last = ordered[-1]
        next_place = min(
            remaining,
            key=lambda x: haversine(
                last.get("lat"),
                last.get("lon"),
                x.get("lat"),
                x.get("lon"),
            ),
        )
        ordered.append(next_place)
        remaining.remove(next_place)

    return ordered


def enrich_place(place: dict) -> dict:
    category = (place.get("category") or "").lower()
    name = (place.get("name") or "").lower()
    summary = (place.get("summary") or "").lower()
    wiki = (place.get("wikipedia_summary") or "").lower()

    text = " ".join([name, summary, wiki]).lower()

    duration = CATEGORY_DURATION.get(category, DEFAULT_DURATION)

    if "museum" in text:
        duration = 120
    elif "aquarium" in text:
        duration = 150
    elif "zoo" in text:
        duration = 180
    elif "beach" in text:
        duration = 120
    elif "riverwalk" in text or "boardwalk" in text:
        duration = 90
    elif "riverfront" in text or "waterfront" in text or "marina" in text or "pier" in text:
        duration = 90
    elif "park" in name:
        duration = 60

    place["estimated_duration_minutes"] = duration
    place["time_of_day_tags"] = CATEGORY_TIME_TAGS.get(category, ["afternoon"])
    return place



def clean_json_response(raw_response: str) -> str:
    raw_response = raw_response.strip()

    if raw_response.startswith("```json"):
        raw_response = raw_response[len("```json"):].strip()
    elif raw_response.startswith("```"):
        raw_response = raw_response[len("```"):].strip()

    if raw_response.endswith("```"):
        raw_response = raw_response[:-3].strip()

    return raw_response


def build_context(places: list[dict]) -> str:
    lines = []

    for p in places:
        name = p.get("name", "Unknown place")
        category = p.get("category", "place")
        address = p.get("address", "Unknown address")
        lat = p.get("lat")
        lon = p.get("lon")
        summary = p.get("summary") or p.get("wikipedia_summary") or ""
        source = p.get("source") or "unknown"

        line = (
            f"- Name: {name} | "
            f"Category: {category} | "
            f"Address: {address} | "
            f"Lat: {lat} | Lon: {lon} | "
            f"Source: {source}"
        )

        if summary:
            line += f" | Summary: {summary}"

        lines.append(line)

    return "\n".join(lines)


def build_prompt(city: str, query: str, num_days: int, pace: str, context: str) -> str:
    query_lower = (query or "").lower()

    extra_rules = ""
    if any(word in query_lower for word in WATERFRONT_QUERY_TERMS):
        extra_rules = """
- For waterfront-style queries, strongly prefer riverwalks, beaches, marinas, piers, boardwalks, bayfront, harbor, and riverfront places.
- Avoid generic neighborhood parks unless they are clearly scenic waterfront destinations.
"""

    return f"""
You are a travel itinerary planner.

Create a high-quality, day-by-day itinerary for the user.

Trip details:
- City: {city}
- User query: {query}
- Number of days: {num_days}
- Pace: {pace}

Candidate places:
{context}

Rules:
- Return ONLY valid JSON.
- Do not include markdown.
- Do not include explanation text.
- Use EXACTLY {num_days} days in the itinerary.
- Use ONLY places from the candidate places list.
- Do NOT invent new places.
- Prioritize the most scenic, iconic, destination-worthy, and relevant places.
- Avoid generic or filler places unless they are clearly strong matches for the user query.
{extra_rules}
- Fewer strong stops are better than many weak stops.
- Group places in a geographically sensible way when possible.
- Each day should feel curated and varied, not like a random list of similar places.
- relaxed pace = fewer stops per day
- balanced pace = medium number of stops per day
- packed pace = more stops per day
- Each day must include a short theme.
- Each stop must include:
  - name
  - category
  - lat
  - lon
  - why_visit
  - time_block

Time block must be one of:
- morning
- afternoon
- evening

Return JSON in exactly this structure:
{{
  "city": "{city}",
  "query": "{query}",
  "num_days": {num_days},
  "pace": "{pace}",
  "itinerary": [
    {{
      "day": 1,
      "theme": "short theme",
      "stops": [
        {{
          "name": "place name",
          "category": "place category",
          "lat": 0.0,
          "lon": 0.0,
          "why_visit": "short reason",
          "time_block": "morning"
        }}
      ]
    }}
  ]
}}
""".strip()


def enrich_itinerary_with_place_data(parsed: dict, places: list[dict]) -> dict:
    place_lookup = {p.get("name"): p for p in places if p.get("name")}

    for day in parsed.get("itinerary", []):
        for stop in day.get("stops", []):
            matched = place_lookup.get(stop.get("name"))
            if matched:
                if stop.get("category") in [None, ""]:
                    stop["category"] = matched.get("category")
                if stop.get("lat") in [None, ""]:
                    stop["lat"] = matched.get("lat")
                if stop.get("lon") in [None, ""]:
                    stop["lon"] = matched.get("lon")

    return parsed


def validate_itinerary_structure(parsed: dict, city: str, query: str, num_days: int, pace: str) -> dict:
    if not isinstance(parsed, dict):
        raise ValueError("Planner output is not a JSON object")

    itinerary = parsed.get("itinerary")
    if not isinstance(itinerary, list):
        raise ValueError("Planner output missing itinerary list")

    if len(itinerary) != num_days:
        raise ValueError(f"Planner returned {len(itinerary)} days instead of {num_days}")

    for expected_day_num, day in enumerate(itinerary, start=1):
        if day.get("day") != expected_day_num:
            day["day"] = expected_day_num

        if not day.get("theme"):
            day["theme"] = f"Day {expected_day_num}"

        stops = day.get("stops")
        if not isinstance(stops, list):
            day["stops"] = []
            continue

        cleaned_stops = []
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            if not stop.get("name"):
                continue

            cleaned_stops.append({
                "name": stop.get("name"),
                "category": stop.get("category"),
                "lat": stop.get("lat"),
                "lon": stop.get("lon"),
                "why_visit": stop.get("why_visit", ""),
                "time_block": (stop.get("time_block") or "afternoon").lower(),
            })

        day["stops"] = cleaned_stops

    parsed["city"] = city
    parsed["query"] = query
    parsed["num_days"] = num_days
    parsed["pace"] = pace

    return parsed


def sort_itinerary_time_blocks(parsed: dict) -> dict:
    for day in parsed.get("itinerary", []):
        stops = day.get("stops", [])
        if isinstance(stops, list):
            day["stops"] = sorted(
                stops,
                key=lambda s: TIME_BLOCK_ORDER.get((s.get("time_block") or "").lower(), 99),
            )
    return parsed


def has_strong_waterfront_signal(text: str) -> bool:
    text = (text or "").lower()
    return any(term in text for term in WATERFRONT_STRONG_TERMS)


def is_anchor_place(text: str) -> bool:
    text = (text or "").lower()
    return any(term in text for term in ANCHOR_TERMS)


def looks_like_generic_park(place: dict) -> bool:
    name = (place.get("name") or "").lower()
    category = (place.get("category") or "").lower()
    summary = (place.get("summary") or "").lower()
    wiki = (place.get("wikipedia_summary") or "").lower()
    tags = " ".join(place.get("tags", [])) if place.get("tags") else ""

    text = " ".join([name, category, summary, wiki, tags]).lower()

    is_anchor = is_anchor_place(text)
    has_strong_waterfront = has_strong_waterfront_signal(text)

    if category == "park" and not is_anchor and not has_strong_waterfront:
        return True

    if "park" in name and not is_anchor and not has_strong_waterfront:
        return True

    return False


def score_place_for_itinerary(place: dict, query: str) -> float:
    score = float(place.get("score", 0.0))

    text = " ".join([
        place.get("name", ""),
        place.get("category", ""),
        place.get("summary", ""),
        place.get("wikipedia_summary", ""),
        " ".join(place.get("tags", [])) if place.get("tags") else "",
    ]).lower()

    query_lower = (query or "").lower()
    category = (place.get("category") or "").lower()

    is_waterfront_query = any(word in query_lower for word in WATERFRONT_QUERY_TERMS)
    is_anchor = is_anchor_place(text)
    has_waterfront_term = has_strong_waterfront_signal(text)
    has_summary = bool(place.get("summary") or place.get("wikipedia_summary"))

    if is_waterfront_query:
        if has_waterfront_term:
            score += 0.12
        if is_anchor:
            score += 0.22
        if has_summary and is_anchor:
            score += 0.06

    if category == "park":
        score -= 0.08

    if category == "park" and not is_anchor:
        score -= 0.30

    if "park" in text and not has_waterfront_term and not is_anchor:
        score -= 0.15

    if not has_summary and not is_anchor:
        score -= 0.08

    return score


def prepare_itinerary_candidates(places: list[dict], query: str, num_days: int, pace: str) -> list[dict]:
    enriched = [enrich_place(dict(p)) for p in places]
    query_lower = (query or "").lower()

    is_waterfront_query = any(word in query_lower for word in WATERFRONT_QUERY_TERMS)

    for place in enriched:
        place["adjusted_score"] = score_place_for_itinerary(place, query)

        text = " ".join([
            place.get("name", ""),
            place.get("category", ""),
            place.get("summary", ""),
            place.get("wikipedia_summary", ""),
            " ".join(place.get("tags", [])) if place.get("tags") else "",
        ]).lower()

        place["is_anchor"] = is_anchor_place(text)
        place["has_summary"] = bool(place.get("summary") or place.get("wikipedia_summary"))
        place["text_blob"] = text

    enriched = [p for p in enriched if p.get("adjusted_score", 0) >= MIN_ITINERARY_SCORE]

    if is_waterfront_query:
        enriched = [
            p for p in enriched
            if (
                p.get("is_anchor", False)
                or has_strong_waterfront_signal(p.get("text_blob", ""))
                or (
                    (p.get("category", "").lower() != "park")
                    and p.get("adjusted_score", 0) >= 0.50
                )
            )
        ]

    enriched.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

    anchors = [p for p in enriched if p.get("is_anchor", False)]
    non_anchors = [p for p in enriched if not p.get("is_anchor", False)]
    enriched = anchors + non_anchors

    max_candidates = PACE_TO_MAX_CANDIDATES.get(pace, 7)
    max_total_stops = num_days * PACE_TO_STOPS_PER_DAY.get(pace, 3)

    enriched = enriched[:max_candidates]
    enriched = enriched[:max_total_stops]

    print("\n=== FILTERED ITINERARY CANDIDATES ===")
    for p in enriched:
        print(
            f"{p.get('name')} | "
            f"category={p.get('category')} | "
            f"adjusted_score={round(p.get('adjusted_score', 0), 4)} | "
            f"is_anchor={p.get('is_anchor')}"
        )

    return enriched



def build_itinerary(results: list[dict], num_days: int = 1, pace: str = "balanced") -> list[dict]:
    enriched = [enrich_place(dict(r)) for r in results]
    ordered = order_by_proximity(enriched)

    if num_days < 1:
        num_days = 1

    daily_limit = PACE_LIMITS.get(pace, 360)
    total_limit = daily_limit * num_days

    selected_places = []
    used_minutes = 0

    for place in ordered:
        duration = place.get("estimated_duration_minutes", DEFAULT_DURATION)
        if used_minutes + duration > total_limit:
            continue
        selected_places.append(place)
        used_minutes += duration

    if not selected_places and ordered:
        selected_places = [ordered[0]]

    day_buckets = [[] for _ in range(num_days)]

    for idx, place in enumerate(selected_places):
        bucket_idx = idx % num_days
        day_buckets[bucket_idx].append(place)

    structured_days = []

    for day_num, day_places in enumerate(day_buckets, start=1):
        used_slots = set()
        stops = []

        for place in day_places:
            slot = assign_slot(place, used_slots)
            used_slots.add(slot)

            stops.append({
                **place,
                "slot": slot,
            })

        structured_days.append({
            "day": day_num,
            "theme": f"Day {day_num} plan",
            "stops": stops,
        })

    return structured_days


def generate_itinerary(city: str, query: str, num_days: int, pace: str, top_k: int):
    print("Planner request:", city, query, num_days, pace, top_k)

    search_output = semantic_search(query, city=city)
    print("semantic_search output type:", type(search_output))
    print("semantic_search output:", search_output)

    if isinstance(search_output, dict):
        places = search_output.get("results", [])
    elif isinstance(search_output, list):
        places = search_output
    else:
        raise ValueError(f"Unexpected semantic_search output type: {type(search_output)}")

    print("places count:", len(places))

    places = places[:top_k]
    places = prepare_itinerary_candidates(
        places,
        query=query,
        num_days=num_days,
        pace=pace,
    )

    if not places:
        return {
            "city": city,
            "query": query,
            "num_days": num_days,
            "pace": pace,
            "itinerary": [
                {
                    "day": day_num,
                    "theme": "No matching attractions found",
                    "stops": [],
                }
                for day_num in range(1, num_days + 1)
            ],
        }

    context = build_context(places)
    print("context built")

    prompt = build_prompt(city, query, num_days, pace, context)
    print("prompt built")
    print(prompt)

    raw_response = generate_text(prompt)
    print("raw llm response:", raw_response)

    if raw_response is None:
        raise ValueError("LLM returned no content")

    raw_response = clean_json_response(raw_response)

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        raise ValueError(f"Planner LLM returned non-JSON output: {raw_response}")

    parsed = validate_itinerary_structure(parsed, city, query, num_days, pace)
    parsed = enrich_itinerary_with_place_data(parsed, places)
    parsed = sort_itinerary_time_blocks(parsed)

    return parsed