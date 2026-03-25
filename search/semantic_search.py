import sys
from services.embedding_service import get_embedding
from services.qdrant_service import search_points
from search.query_interpreter import interpret_query
import re

def normalize_name(name: str) -> str:
    name = name.lower()

    # remove punctuation
    name = re.sub(r"[^\w\s]", "", name)

    # remove common stopwords
    STOPWORDS = {"the", "at", "of", "and"}
    tokens = [t for t in name.split() if t not in STOPWORDS]

    return " ".join(tokens)

PREFERRED_CATEGORIES = {
    "theme_park": 0.10,
    "museum": 0.08,
    "gallery": 0.06,
    "zoo": 0.08,
    "aquarium": 0.08,
    "nature_reserve": 0.07,
    "park": 0.05,
    "attraction": 0.04,
    "artwork": 0.01,
}

WEAK_NAME_TERMS = {
    "name art",
    "art",
    "attraction",
    "park",
}

THEME_PARK_QUERY_TERMS = {
    "theme park",
    "amusement park",
    "water park",
}

THEME_PARK_STRONG_MATCH_TERMS = {
    "theme park",
    "amusement park",
    "water park",
    "roller coaster",
    "rides",
}

BAD_PARK_TERMS = {
    "technology park",
    "tech park",
    "industrial park",
    "office park",
    "business park",
    "research park",
}

LOW_VALUE_ACTIVITY_TERMS = {
    "ride",
    "coaster",
    "carousel",
    "train",
    "pony ride",
    "petting zoo",
    "bumper boats",
    "swing",
    "play area",
    "kids area",
    "mini",
    "junior",
}

MAJOR_THEME_PARK_VENUE_TERMS = {
    "busch gardens",
    "adventure island",
    "disney",
    "universal",
    "legoland",
    "seaworld",
}

ANCHOR_ATTRACTION_TERMS = {
    "zoo",
    "aquarium",
    "museum",
    "botanical garden",
    "science center",
    "wildlife",
}

WATERFRONT_QUERY_TERMS = {
    "waterfront",
    "riverfront",
    "scenic waterfront",
    "bayfront",
    "harbor",
    "harbour",
    "beach",
    "river walk",
    "riverwalk",
    "boardwalk",
    "marina",
    "pier",
    "shore",
}

WATERFRONT_STRONG_MATCH_TERMS = {
    "waterfront",
    "riverfront",
    "riverwalk",
    "river walk",
    "bay",
    "bayfront",
    "harbor",
    "harbour",
    "beach",
    "shore",
    "marina",
    "pier",
    "boardwalk",
    "canal",
    "island",
}

LOW_VALUE_GENERIC_PARK_TERMS = {
    "neighborhood park",
    "community park",
    "city park",
}


def get_payload(result):
    return result.payload if hasattr(result, "payload") else result.get("payload", {})


def get_score(result):
    raw_score = result.score if hasattr(result, "score") else result.get("score", 0.0)
    return float(raw_score)


def is_close(lat1, lon1, lat2, lon2, threshold=0.01):
    if not all([lat1, lon1, lat2, lon2]):
        return False
    return abs(lat1 - lat2) < threshold and abs(lon1 - lon2) < threshold


def deduplicate_results(results):
    deduped = []

    for r in results:
        payload = get_payload(r)

        name = normalize_name(payload.get("name") or "")
        lat = payload.get("lat")
        lon = payload.get("lon")
        category = payload.get("category")

        is_duplicate = False

        for existing in deduped:
            existing_payload = get_payload(existing)

            existing_name = normalize_name(existing_payload.get("name") or "")
            existing_lat = existing_payload.get("lat")
            existing_lon = existing_payload.get("lon")

            # name similarity OR same location
            if (
                name == existing_name
                or is_close(lat, lon, existing_lat, existing_lon)
            ):
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(r)

    return deduped


def build_search_text(payload):
    name = (payload.get("name") or "").strip().lower()
    category = (payload.get("category") or "").strip().lower()
    address = (payload.get("address") or "").strip().lower()

    summary = (
        payload.get("wikipedia_summary")
        or payload.get("yelp_review_summary")
        or ""
    ).strip().lower()

    source = (payload.get("source") or "").strip().lower()
    city = (payload.get("city") or "").strip().lower()

    return " ".join(
        part for part in [name, category, address, summary, source, city] if part
    )


def contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def rerank_results(results, interpreted):
    categories = interpreted.get("categories", [])
    intents = interpreted.get("intents", [])
    normalized_query = interpreted.get("normalized_query", "")

    is_theme_park_query = contains_any(normalized_query, THEME_PARK_QUERY_TERMS)
    is_waterfront_query = contains_any(normalized_query, WATERFRONT_QUERY_TERMS)
    reranked = []

    for r in results:
        payload = get_payload(r)
        base_score = get_score(r)

        name = (payload.get("name") or "").strip()
        name_lower = name.lower()
        category = payload.get("category")
        rating = payload.get("yelp_rating")

        has_summary = payload.get("has_summary", False)
        has_address = payload.get("has_address", False)
        is_downtown_like = payload.get("is_downtown_like", False)
        is_family_friendly_like = payload.get("is_family_friendly_like", False)
        is_cultural_like = payload.get("is_cultural_like", False)
        is_nature_like = payload.get("is_nature_like", False)

        search_text = build_search_text(payload)
        is_low_value = contains_any(name_lower, LOW_VALUE_ACTIVITY_TERMS)
        is_waterfront_match = contains_any(search_text, WATERFRONT_STRONG_MATCH_TERMS)
        is_generic_park = (
            category == "park"
            and not is_waterfront_match
        )
        adjusted_score = base_score

        if has_summary:
            adjusted_score += 0.08

        if has_address:
            adjusted_score += 0.04

        if category in PREFERRED_CATEGORIES:
            adjusted_score += PREFERRED_CATEGORIES[category]

        if categories and category in categories:
            adjusted_score += 0.08

        if rating is not None:
            try:
                adjusted_score += min(float(rating) / 100.0, 0.05)
            except Exception:
                pass

        if name_lower in WEAK_NAME_TERMS:
            adjusted_score -= 0.08

        if not has_address and not has_summary:
            adjusted_score -= 0.06

        if contains_any(search_text, ANCHOR_ATTRACTION_TERMS):
            adjusted_score += 0.20

        # Penalize low-value activity/sub-ride style results
        if is_low_value:
            adjusted_score -= 0.25

        if is_low_value and len(name_lower.split()) <= 3:
            adjusted_score -= 0.10

        # Theme park specific handling
        if is_theme_park_query:
            if category == "theme_park":
                adjusted_score += 0.18

            if contains_any(search_text, THEME_PARK_STRONG_MATCH_TERMS):
                adjusted_score += 0.20

            if contains_any(search_text, BAD_PARK_TERMS):
                adjusted_score -= 0.35

            if category == "park" and not contains_any(search_text, THEME_PARK_STRONG_MATCH_TERMS):
                adjusted_score -= 0.10

            if category in {"zoo", "aquarium", "attraction"}:
                adjusted_score += 0.03

            if contains_any(search_text, MAJOR_THEME_PARK_VENUE_TERMS):
                adjusted_score += 0.18


        if is_waterfront_query:
            if is_waterfront_match:
                adjusted_score += 0.16

            if category in {"park", "attraction"} and is_waterfront_match:
                adjusted_score += 0.06

            if is_downtown_like and is_waterfront_match:
                adjusted_score += 0.05

            if has_summary and is_waterfront_match:
                adjusted_score += 0.04

            if category == "park" and not is_waterfront_match:
                adjusted_score -= 0.14

            if contains_any(search_text, LOW_VALUE_GENERIC_PARK_TERMS):
                adjusted_score -= 0.10


        if "family" in intents:
            if category in {"zoo", "aquarium", "museum", "attraction", "theme_park"}:
                adjusted_score += 0.06
            if is_family_friendly_like:
                adjusted_score += 0.05

        if "family_fun" in intents:
            if category in {"theme_park", "zoo", "aquarium", "attraction"}:
                adjusted_score += 0.08
            if contains_any(search_text, THEME_PARK_STRONG_MATCH_TERMS):
                adjusted_score += 0.06

        if "art_culture" in intents:
            if category in {"museum", "gallery"}:
                adjusted_score += 0.08
            if is_cultural_like:
                adjusted_score += 0.05
            if category == "artwork" and not has_summary:
                adjusted_score -= 0.03

        if "history" in intents:
            if category == "museum":
                adjusted_score += 0.06
            if is_cultural_like:
                adjusted_score += 0.04

        if "nature" in intents:
            if category in {"park", "nature_reserve"}:
                adjusted_score += 0.08
            if is_nature_like:
                adjusted_score += 0.05

        if "tourist" in intents:
            if category in {"museum", "attraction", "gallery", "park", "theme_park"}:
                adjusted_score += 0.05
            if has_address:
                adjusted_score += 0.03
            if is_cultural_like or is_downtown_like:
                adjusted_score += 0.04

        if "short_visit" in intents:
            if category in {"museum", "gallery", "artwork", "attraction"}:
                adjusted_score += 0.04
            if has_summary:
                adjusted_score += 0.02

        if "downtown" in intents:
            if has_address:
                adjusted_score += 0.05
            if is_downtown_like:
                adjusted_score += 0.08

        # Controlled filtering of low-value results
        # Strict filtering for theme park queries
        is_anchor = contains_any(search_text, ANCHOR_ATTRACTION_TERMS)
        strong_theme_park_venue = contains_any(search_text, MAJOR_THEME_PARK_VENUE_TERMS)

        if is_theme_park_query:
            if is_low_value and not strong_theme_park_venue:
                continue

        elif is_waterfront_query:
            if category == "park" and not is_waterfront_match and adjusted_score < 0.30:
                continue

        else:
            if is_low_value and not is_anchor and adjusted_score < 0.25:
                continue

        reranked.append((adjusted_score, r))

    reranked.sort(key=lambda x: x[0], reverse=True)
    return reranked



def format_results(reranked_results):
    formatted = []

    for adjusted_score, r in reranked_results:
        payload = get_payload(r)

        formatted.append({
            "score": round(adjusted_score, 4),
            "name": payload.get("name"),
            "category": payload.get("category"),
            "address": payload.get("address"),
            "city": payload.get("city"),
            "source": payload.get("source"),
            "source_id": payload.get("source_id"),
            "lat": payload.get("lat"),
            "lon": payload.get("lon"),
            "summary": payload.get("wikipedia_summary") or payload.get("yelp_review_summary"),
            "rating": payload.get("yelp_rating"),
            "has_summary": payload.get("has_summary"),
            "has_address": payload.get("has_address"),
            "is_downtown_like": payload.get("is_downtown_like"),
            "is_family_friendly_like": payload.get("is_family_friendly_like"),
            "is_cultural_like": payload.get("is_cultural_like"),
            "is_nature_like": payload.get("is_nature_like"),
        })

    return formatted


def semantic_search(query: str, city: str = "Tampa", top_k: int = 10, debug: bool = False) -> dict:
    interpreted = interpret_query(query)
    categories = interpreted.get("categories", [])

    query_vector = get_embedding(query)

    raw_results = search_points(
        query_vector=query_vector,
        limit=top_k * 3,
        categories=categories if categories else None,
    )

    deduped = deduplicate_results(raw_results)
    reranked = rerank_results(deduped, interpreted)
    formatted = format_results(reranked[:top_k])

    response = {
        "query": query,
        "city": city,
        "categories": interpreted.get("categories", []),
        "intents": interpreted.get("intents", []),
        "results": formatted,
    }

    if debug:
        response["counts"] = {
            "raw_results": len(raw_results),
            "deduped_results": len(deduped),
            "returned_results": len(formatted),
        }

    return response


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "family friendly museum with history"

    response = semantic_search(query, top_k=5)

    print(f"\nQuery: {response['query']}")
    print(f"City: {response['city']}")
    print(f"Inferred categories: {response['categories']}")
    print(f"Inferred intents: {response['intents']}")
    print()

    for i, item in enumerate(response["results"], 1):
        print(f"{i}. {item['name']} ({item['category']})")
        print(f"   Score: {item['score']:.4f}")
        print(f"   Address: {item['address']}")
        print(f"   Rating: {item['rating']}")
        print(f"   has_summary: {item['has_summary']}")
        print(f"   has_address: {item['has_address']}")
        print(f"   is_downtown_like: {item['is_downtown_like']}")
        print(f"   is_family_friendly_like: {item['is_family_friendly_like']}")
        print(f"   is_cultural_like: {item['is_cultural_like']}")
        print(f"   is_nature_like: {item['is_nature_like']}")
        print(f"   Summary: {item['summary']}")
        print()