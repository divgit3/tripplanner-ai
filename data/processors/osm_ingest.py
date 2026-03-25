import json
from pathlib import Path
from collections import Counter
from data.clients.osm_client import fetch_osm_places
from data.processors.osm_cleaner import clean_osm_elements


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ingest_city_osm(city: str) -> dict:
    raw_data = fetch_osm_places(city)
    cleaned_places = clean_osm_elements(raw_data, city)

    city_slug = city.lower().replace(" ", "_")

    raw_path = RAW_DIR / f"osm_{city_slug}.json"
    processed_path = PROCESSED_DIR / f"places_{city_slug}.json"
    category_counts = Counter(place.category for place in cleaned_places)

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(
            [place.model_dump() for place in cleaned_places],
            f,
            ensure_ascii=False,
            indent=2,
        )

    return {
        "city": city,
        "raw_elements": len(raw_data.get("elements", [])),
        "cleaned_places": len(cleaned_places),
        "category_counts": dict(category_counts),
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
    }