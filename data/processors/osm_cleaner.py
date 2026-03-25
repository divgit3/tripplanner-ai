import re
from typing import Optional, Dict, List

from data.schemas.place import Place


ALLOWED_TAGS = {
    "tourism": {
        "attraction",
        "museum",
        "gallery",
        "viewpoint",
        "zoo",
        "theme_park",
        "aquarium",
        "artwork",
        "yes",
    },
    "historic": {
        "monument",
        "memorial",
        "castle",
        "ruins",
        "archaeological_site",
        "building",
    },
    "leisure": {
        "park",
        "garden",
        "nature_reserve",
        "beach_resort",
    },
    "amenity": {
        "arts_centre",
        "planetarium",
    },
    "natural": {
        "beach",
        "peak",
        "cave_entrance",
        "waterfall",
    },
}
EXCLUDED_NAME_KEYWORDS = {
    "playground"
}


def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\s+", " ", name)
    return name


def extract_lat_lon(element: dict) -> Optional[tuple[float, float]]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]

    center = element.get("center")
    if center and "lat" in center and "lon" in center:
        return center["lat"], center["lon"]

    return None


def is_relevant(tags: Dict[str, str]) -> bool:
    for key, allowed_values in ALLOWED_TAGS.items():
        if key in tags and tags[key] in allowed_values:
            return True
    return False


def map_category(tags: Dict[str, str]) -> Optional[str]:
    if "tourism" in tags and tags["tourism"] in ALLOWED_TAGS["tourism"]:
        return tags["tourism"]

    if "historic" in tags and tags["historic"] in ALLOWED_TAGS["historic"]:
        return f"historic_{tags['historic']}"

    if "leisure" in tags and tags["leisure"] in ALLOWED_TAGS["leisure"]:
        return tags["leisure"]

    if "amenity" in tags and tags["amenity"] in ALLOWED_TAGS["amenity"]:
        return tags["amenity"]

    if "natural" in tags and tags["natural"] in ALLOWED_TAGS["natural"]:
        return tags["natural"]

    return None


def build_subcategories(tags: Dict[str, str]) -> List[str]:
    subcategories = []

    for key in ALLOWED_TAGS:
        if key in tags:
            subcategories.append(f"{key}:{tags[key]}")

    return subcategories


def build_address(tags: Dict[str, str]) -> Optional[str]:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    parts = [part for part in parts if part]
    return ", ".join(parts) if parts else None


def should_exclude_by_name(name: str) -> bool:
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in EXCLUDED_NAME_KEYWORDS)


def clean_osm_elements(raw_data: dict, city: str) -> List[Place]:
    elements = raw_data.get("elements", [])
    cleaned_places: List[Place] = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")

        if not name:
            continue

        if should_exclude_by_name(name):
            continue

        if not is_relevant(tags):
            continue

        coords = extract_lat_lon(element)
        if not coords:
            continue

        lat, lon = coords

        dedupe_key = f"{normalize_name(name)}_{round(lat, 4)}_{round(lon, 4)}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        place = Place(
            source="osm",
            source_id=f"{element['type']}_{element['id']}",
            name=name,
            city=city,
            lat=lat,
            lon=lon,
            category=map_category(tags),
            subcategories=build_subcategories(tags),
            address=build_address(tags),
            website=tags.get("website") or tags.get("contact:website"),
            phone=tags.get("phone") or tags.get("contact:phone"),
            tags=tags,
        )

        cleaned_places.append(place)

    return cleaned_places