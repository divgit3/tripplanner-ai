from typing import List, Dict


CATEGORY_RULES = {
    "theme_park": [
        "theme park", "amusement park", "water park", "roller coaster", "rides"
    ],
    "museum": [
        "museum", "history", "historic", "exhibit", "architecture", "culture"
    ],
    "park": [
        "park", "outdoor", "walk", "trail", "picnic", "garden", "scenic"
    ],
    "nature_reserve": [
        "nature", "preserve", "wildlife", "quiet", "hike", "wilderness"
    ],
    "zoo": [
        "zoo", "animals", "animal"
    ],
    "aquarium": [
        "aquarium", "marine", "sea life", "fish", "underwater"
    ],
    "gallery": [
        "gallery", "art", "artist", "exhibition"
    ],
}


INTENT_RULES = {
    "downtown": ["downtown", "city center", "central"],
    "tourist": ["tourist", "must see", "landmark", "popular", "sightseeing"],
    "short_visit": ["short visit", "quick", "1 hour", "2 hours", "brief"],
    "family": ["family", "kids", "children", "child-friendly", "family-friendly"],
    "art_culture": ["art", "culture", "gallery", "museum"],
    "history": ["history", "historic", "heritage"],
    "nature": ["nature", "outdoor", "park", "walk", "trail", "scenic", "quiet"],
    "family_fun": ["theme park", "amusement park", "water park", "rides"],
}


def normalize_query(query: str) -> str:
    return query.lower().strip()


def infer_categories(query: str) -> List[str]:
    q = normalize_query(query)
    matched_categories = []

    # 1. Specific theme/amusement/water park detection first
    if any(term in q for term in ["theme park", "amusement park", "water park"]):
        matched_categories.append("theme_park")

    # 2. Generic keyword matching
    for category, keywords in CATEGORY_RULES.items():
        if category == "theme_park":
            continue  # already handled above

        for keyword in keywords:
            if keyword in q:
                # Avoid adding generic "park" for theme/amusement/water park queries
                if category == "park" and any(
                    term in q for term in ["theme park", "amusement park", "water park"]
                ):
                    continue

                matched_categories.append(category)
                break

    return matched_categories


def infer_intents(query: str) -> List[str]:
    q = normalize_query(query)
    matched_intents = []

    for intent, keywords in INTENT_RULES.items():
        for keyword in keywords:
            if keyword in q:
                matched_intents.append(intent)
                break

    return matched_intents


def interpret_query(query: str) -> Dict:
    normalized_query = normalize_query(query)
    categories = infer_categories(query)
    intents = infer_intents(query)

    return {
        "original_query": query,
        "normalized_query": normalized_query,
        "categories": categories,
        "intents": intents,
    }