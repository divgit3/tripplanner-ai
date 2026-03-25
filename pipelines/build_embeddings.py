import json
from pathlib import Path
from qdrant_client.models import PointStruct

from services.embedding_service import get_embedding
from services.qdrant_service import recreate_collection, upsert_points


INPUT_PATH = Path("data/processed/places_tampa_enriched.json")
OUTPUT_DEBUG_PATH = Path("data/processed/places_tampa_search_ready.json")


def build_search_text(place: dict) -> str:
    parts = []

    name = place.get("name")
    city = place.get("city")
    category = place.get("category")
    subcategories = place.get("subcategories") or []
    address = place.get("address")
    wiki_summary = place.get("wikipedia_summary")
    yelp_summary = place.get("yelp_review_summary")
    rating = place.get("yelp_rating")
    review_count = place.get("yelp_review_count")

    if name and city:
        parts.append(f"{name} is a place to visit in {city}.")
    elif name:
        parts.append(f"{name} is a place to visit.")

    if category:
        parts.append(f"It is a {category}.")

    if subcategories:
        parts.append(f"Related tags: {', '.join(subcategories)}.")

    if address:
        parts.append(f"It is located at {address}.")

    if wiki_summary:
        parts.append(f"About the place: {wiki_summary}")

    if yelp_summary:
        parts.append(f"Visitor impressions: {yelp_summary}")

    if rating is not None and review_count is not None:
        parts.append(f"It has a rating of {rating} from {review_count} reviews.")

    return " ".join(parts).strip()


def infer_derived_flags(place: dict) -> dict:
    name = (place.get("name") or "").lower()
    category = (place.get("category") or "").lower()
    subcategories = " ".join(place.get("subcategories") or []).lower()
    address = (place.get("address") or "").lower()
    wiki_summary = (place.get("wikipedia_summary") or "").lower()
    yelp_summary = (place.get("yelp_review_summary") or "").lower()

    combined_text = " ".join([
        name,
        category,
        subcategories,
        address,
        wiki_summary,
        yelp_summary,
    ])

    downtown_terms = [
        "downtown",
        "water street",
        "gasparilla plaza",
        "riverwalk",
        "channelside",
        "franklin street",
        "tampa riverwalk",
        "33602",
    ]

    family_terms = [
        "family",
        "children",
        "child",
        "kids",
        "kid",
        "zoo",
        "aquarium",
        "interactive",
        "petting",
        "play",
    ]

    cultural_terms = [
        "museum",
        "gallery",
        "art",
        "history",
        "historic",
        "heritage",
        "culture",
        "cultural",
        "exhibit",
        "architecture",
    ]

    nature_terms = [
        "nature",
        "park",
        "trail",
        "walk",
        "outdoor",
        "preserve",
        "wildlife",
        "garden",
        "wilderness",
        "scenic",
    ]

    return {
        "has_summary": bool(place.get("wikipedia_summary") or place.get("yelp_review_summary")),
        "has_address": bool(place.get("address")),
        "is_downtown_like": any(term in combined_text for term in downtown_terms),
        "is_family_friendly_like": any(term in combined_text for term in family_terms),
        "is_cultural_like": any(term in combined_text for term in cultural_terms),
        "is_nature_like": any(term in combined_text for term in nature_terms),
    }


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        places = json.load(f)

    enriched_places = []
    for place in places:
        search_text = build_search_text(place)
        if search_text:
            place["search_text"] = search_text
            place["derived_flags"] = infer_derived_flags(place)
            enriched_places.append(place)

    if not enriched_places:
        print("No places with searchable text found.")
        return

    first_vector = get_embedding(enriched_places[0]["search_text"])
    vector_size = len(first_vector)
    recreate_collection(vector_size)

    points = []
    for idx, place in enumerate(enriched_places):
        vector = first_vector if idx == 0 else get_embedding(place["search_text"])
        flags = place.get("derived_flags", {})

        payload = {
            "source_id": place.get("source_id"),
            "name": place.get("name"),
            "city": place.get("city"),
            "category": place.get("category"),
            "subcategories": place.get("subcategories"),
            "address": place.get("address"),
            "wikipedia_title": place.get("wikipedia_title"),
            "wikipedia_summary": place.get("wikipedia_summary"),
            "yelp_rating": place.get("yelp_rating"),
            "yelp_review_count": place.get("yelp_review_count"),
            "yelp_review_summary": place.get("yelp_review_summary"),
            "lat": place.get("lat"),
            "lon": place.get("lon"),
            "search_text": place.get("search_text"),
            "has_summary": flags.get("has_summary", False),
            "has_address": flags.get("has_address", False),
            "is_downtown_like": flags.get("is_downtown_like", False),
            "is_family_friendly_like": flags.get("is_family_friendly_like", False),
            "is_cultural_like": flags.get("is_cultural_like", False),
            "is_nature_like": flags.get("is_nature_like", False),
        }

        points.append(
            PointStruct(
                id=idx + 1,
                vector=vector,
                payload=payload
            )
        )

        if len(points) == 50:
            upsert_points(points)
            print(f"Upserted {idx + 1} places...")
            points = []

    if points:
        upsert_points(points)
        print(f"Upserted final batch. Total places: {len(enriched_places)}")

    with open(OUTPUT_DEBUG_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched_places, f, ensure_ascii=False, indent=2)

    print(f"Saved debug file to: {OUTPUT_DEBUG_PATH}")
    print("Done building embeddings and indexing into Qdrant.")


if __name__ == "__main__":
    main()