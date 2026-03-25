from __future__ import annotations

import json
from pathlib import Path
from typing import List

from services.wikipedia_service import WikipediaService
from utils.wiki_filters import should_enrich_with_wikipedia


def build_search_text(place: dict) -> str:
    parts = [
        place.get("name") or "",
        place.get("category") or "",
        " ".join(place.get("subcategories") or []),
        place.get("address") or "",
        place.get("wikipedia_summary") or "",
    ]
    return ". ".join([p for p in parts if p]).strip()


def enrich_places_with_wikipedia(
    input_path: str,
    output_path: str,
    city: str,
    state: str = "Florida",
    max_places: int | None = None,
) -> None:
    wiki = WikipediaService()

    input_file = Path(input_path)
    output_file = Path(output_path)

    with input_file.open("r", encoding="utf-8") as f:
        places: List[dict] = json.load(f)

    enriched_count = 0
    checked_count = 0

    for place in places:
        # default values for all places
        place["wikipedia_title"] = place.get("wikipedia_title")
        place["wikipedia_summary"] = place.get("wikipedia_summary")
        place["wikipedia_url"] = place.get("wikipedia_url")

        if should_enrich_with_wikipedia(place):
            if max_places is None or checked_count < max_places:
                checked_count += 1
                name = place.get("name")

                result = wiki.enrich_place(name=name, city=city, state=state)

                if result:
                    place["wikipedia_title"] = result["title"]
                    place["wikipedia_summary"] = result["summary"]
                    place["wikipedia_url"] = result["url"]
                    enriched_count += 1
                    print(f"[OK] {name} -> {result['title']}")
                else:
                    place["wikipedia_title"] = None
                    place["wikipedia_summary"] = None
                    place["wikipedia_url"] = None
                    print(f"[MISS] {name}")

        # Step 3: add search_text for every place
        place["search_text"] = build_search_text(place)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)

    print("\nDone.")
    print(f"Checked candidate places: {checked_count}")
    print(f"Enriched places: {enriched_count}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    enrich_places_with_wikipedia(
        input_path="data/processed/places_tampa.json",
        output_path="data/processed/places_tampa_enriched.json",
        city="Tampa",
        state="Florida",
    )