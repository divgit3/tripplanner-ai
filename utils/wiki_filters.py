WIKI_ALLOWED_CATEGORIES = {
    "museum",
    "zoo",
    "aquarium",
    "beach",
    "gallery",
    "theatre",
    "theater",
    "stadium",
    "university",
    "memorial",
    "monument",
    "garden",
    "botanical_garden",
    "library",
    "park",
}

BLOCKLIST_EXACT_NAMES = {
    "maze",
    "train",
    "pony ride",
    "petting zoo",
    "name art",
    "jungle carousel",
    "science discovery center",
    "giraffe feeding & viewing",
    "treehouse trek",
}

BLOCKLIST_TERMS = {
    "gazebo",
    "carousel",
    "coaster",
    "boats",
    "ride",
    "bust",
    "statue",
    "cruise port",
    "trek",
    "courtyard",
}

def should_enrich_with_wikipedia(place: dict) -> bool:
    name = (place.get("name") or "").strip().lower()
    category = (place.get("category") or "").strip().lower()

    if not name or len(name) < 4:
        return False

    if name in BLOCKLIST_EXACT_NAMES:
        return False

    if any(term in name for term in BLOCKLIST_TERMS):
        return False

    if category in WIKI_ALLOWED_CATEGORIES:
        return True

    subcategories = [s.lower() for s in (place.get("subcategories") or [])]
    if any(s.startswith("tourism:museum") for s in subcategories):
        return True
    if any(s.startswith("tourism:gallery") for s in subcategories):
        return True
    if any(s.startswith("tourism:zoo") for s in subcategories):
        return True
    if any(s.startswith("tourism:attraction") for s in subcategories):
        return True

    return False