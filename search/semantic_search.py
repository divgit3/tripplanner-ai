import sys
from services.embedding_service import get_embedding
from services.qdrant_service import search_points
from search.query_interpreter import interpret_query
from search.filters import deduplicate_results
from search.ranking import rerank_results
from search.diversification import diversify_results

def get_payload(result):
    return result.payload if hasattr(result, "payload") else result.get("payload", {})


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
    reranked = diversify_results(reranked)
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