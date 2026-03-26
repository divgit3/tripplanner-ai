from typing import List, Dict


CATEGORY_RULES = {
    "theme_park": [
        "theme park", "amusement park", "water park", "roller coaster", "rides"
    ],
    "museum": [
        "museum", "history museum", "historic museum", "exhibit", "architecture",
        "science center", "cultural center"
    ],
    "park": [
        "park", "outdoor", "walk", "trail", "picnic", "garden", "scenic",
        "botanical garden", "riverwalk", "waterfront", "riverfront"
    ],
    "nature_reserve": [
        "nature", "preserve", "wildlife", "quiet", "hike", "wilderness",
        "birding", "nature walk"
    ],
    "zoo": [
        "zoo", "animals", "animal"
    ],
    "aquarium": [
        "aquarium", "marine", "sea life", "fish", "underwater"
    ],
    "gallery": [
        "gallery", "art gallery", "artist", "exhibition"
    ],
    "attraction": [
        "attraction", "landmark", "must see", "iconic", "tourist spot"
    ],
}


INTENT_RULES = {
    "downtown": ["downtown", "city center", "central"],
    "tourist": ["tourist", "must see", "landmark", "popular", "sightseeing", "iconic"],
    "short_visit": ["short visit", "quick", "1 hour", "2 hours", "brief"],
    "family": ["family", "kids", "children", "child-friendly", "family-friendly"],
    "family_fun": ["theme park", "amusement park", "water park", "rides", "interactive"],
    "art_culture": ["art", "culture", "gallery", "museum", "art and culture"],
    "history": ["history", "historic", "heritage"],
    "nature": ["nature", "outdoor", "park", "walk", "trail", "scenic", "quiet"],
    "romantic": ["romantic", "couples", "date", "sunset", "getaway"],
    "waterfront": ["waterfront", "riverfront", "riverwalk", "bayfront", "harbor", "beach", "pier", "marina"],
    "indoor": ["indoor", "inside", "air conditioned"],
    "hidden_gem": ["hidden gem", "local gem", "less crowded", "offbeat"],
    "relaxation": ["relaxing", "relaxation", "calm", "peaceful"],
    "quiet": ["quiet", "peaceful", "calm", "less crowded", "serene"]
}


def normalize_query(query: str) -> str:
    return query.lower().strip()


def infer_categories(query: str) -> List[str]:
    q = normalize_query(query)
    matched_categories = []

    is_theme_park_query = any(
        term in q for term in ["theme park", "amusement park", "water park"]
    )

    if is_theme_park_query:
        matched_categories.append("theme_park")

    for category, keywords in CATEGORY_RULES.items():
        if category == "theme_park":
            continue

        for keyword in keywords:
            if keyword in q:
                if category == "park" and is_theme_park_query:
                    continue
                matched_categories.append(category)
                break

    return list(dict.fromkeys(matched_categories))


def infer_intents(query: str) -> List[str]:
    q = normalize_query(query)
    matched_intents = []

    for intent, keywords in INTENT_RULES.items():
        for keyword in keywords:
            if keyword in q:
                matched_intents.append(intent)
                break

    return list(dict.fromkeys(matched_intents))


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