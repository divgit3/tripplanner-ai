
THEME_PARK_QUERY_TERMS = {
    "theme park",
    "amusement park",
    "water park",
}

URBAN_WALK_TERMS = {
    "riverwalk",
    "downtown",
    "city",
    "urban",
    "boulevard",
    "marina",
    "waterfront",
    "bayfront",
    "boardwalk",
}

QUIET_STRONG_MATCH_TERMS = {
    "quiet",
    "peaceful",
    "serene",
    "preserve",
    "nature",
    "trail",
    "garden",
    "botanical",
    "wilderness",
    "birding",
}

LOW_VALUE_WALK_TERMS = {
    "dog walk",
    "dog park",
    "walk loop",
    "loop",
    "exercise trail",
    "fitness trail",
}

WALK_STRONG_MATCH_TERMS = {
    "trail",
    "boardwalk",
    "walk",
    "walking",
    "nature walk",
    "hiking",
    "hike",
    "loop",
    "riverwalk",
    "path",
}

THEME_PARK_STRONG_MATCH_TERMS = {
    "theme park",
    "amusement park",
    "water park",
    "roller coaster",
    "rides",
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

LOW_VALUE_GENERIC_PARK_TERMS = {
    "neighborhood park",
    "community park",
    "city park",
}

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

BAD_PARK_TERMS = {
    "technology park",
    "tech park",
    "industrial park",
    "office park",
    "business park",
    "research park",
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


def get_payload(result):
    return result.payload if hasattr(result, "payload") else result.get("payload", {})


def get_score(result):
    raw_score = result.score if hasattr(result, "score") else result.get("score", 0.0)
    return float(raw_score)


def contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


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
        category = (payload.get("category") or "").strip().lower()
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
        is_walk_match = contains_any(search_text, WALK_STRONG_MATCH_TERMS)
        is_low_value_walk = contains_any(search_text, LOW_VALUE_WALK_TERMS)
        is_urban_walk = contains_any(search_text, URBAN_WALK_TERMS)
        is_quiet_match = contains_any(search_text, QUIET_STRONG_MATCH_TERMS)

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
            adjusted_score -= 0.16
        elif not has_address:
            adjusted_score -= 0.06
        elif not has_summary:
            adjusted_score -= 0.05

        if contains_any(search_text, ANCHOR_ATTRACTION_TERMS):
            adjusted_score += 0.20

        if is_low_value:
            adjusted_score -= 0.25

        if is_low_value and len(name_lower.split()) <= 3:
            adjusted_score -= 0.10

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
            if is_walk_match:
                adjusted_score += 0.06
            if is_low_value_walk:
                adjusted_score -= 0.12
            if has_summary:
                adjusted_score += 0.03
            if has_address:
                adjusted_score += 0.02

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

        if "hidden_gem" in intents:
            if has_summary:
                adjusted_score += 0.04
            if has_address:
                adjusted_score += 0.03
            if is_nature_like or is_cultural_like:
                adjusted_score += 0.03
            if not has_summary and not has_address:
                adjusted_score -= 0.15
            if not is_downtown_like:
                adjusted_score += 0.02


        if "quiet" in intents:
            if is_quiet_match:
                adjusted_score += 0.06
            if category in {"nature_reserve"}:
                adjusted_score += 0.05
            if "garden" in search_text or "contemplation" in search_text:
                adjusted_score += 0.06
            if is_downtown_like:
                adjusted_score -= 0.12
            if is_urban_walk:
                adjusted_score -= 0.12
            if is_waterfront_match:
                adjusted_score -= 0.04


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
        
        if "nature" in intents:
            if not has_summary and not has_address and adjusted_score < 0.45:
                continue

        if "hidden_gem" in intents:
            if not has_summary and not has_address and adjusted_score < 0.52:
                continue

        reranked.append((adjusted_score, r))

    reranked.sort(key=lambda x: x[0], reverse=True)
    return reranked