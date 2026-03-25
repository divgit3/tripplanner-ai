from typing import List, Dict, Any
from services.llm_service import get_openai_client
from search.semantic_search import semantic_search   # replace with your real function name


SYSTEM_PROMPT = """
You are TripPlanner-AI, a grounded travel assistant.

Rules:
- Only use the provided context
- Do not invent places or facts
- If data is missing, say so
- Recommend the top 3 to 5 places clearly
- Be concise and helpful
""".strip()


def _safe_get(item: Any, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def retrieve_places(city: str, query: str, top_k: int) -> List[Dict[str, Any]]:
    search_output = semantic_search(query=query, city=city, top_k=top_k)

    if isinstance(search_output, dict):
        results = search_output.get("results", [])
    else:
        results = search_output or []

    normalized = []
    for r in results:
        normalized.append({
            "name": _safe_get(r, "name"),
            "category": _safe_get(r, "category"),
            "address": _safe_get(r, "address"),
            "city": _safe_get(r, "city"),
            "wikipedia_summary": _safe_get(r, "wikipedia_summary"),
            "yelp_review_summary": _safe_get(r, "yelp_review_summary"),
            "score": _safe_get(r, "score"),
            "source": _safe_get(r, "source"),
            "source_id": _safe_get(r, "source_id"),
            "lat": _safe_get(r, "lat"),
            "lon": _safe_get(r, "lon"),
        })
    return normalized


def build_context(places: List[Dict[str, Any]]) -> str:
    chunks = []

    for i, p in enumerate(places[:3], start=1):
        wiki = (p.get("wikipedia_summary") or "N/A")[:400]
        yelp = (p.get("yelp_review_summary") or "N/A")[:250]
        address = p.get("address") or "Not available"

        chunk = f"""
Place {i}:
Name: {p.get('name') or 'Unknown'}
Category: {p.get('category') or 'N/A'}
f"Address: {address}"
Wikipedia: {wiki}
Yelp: {yelp}
Score: {p.get('score')}
""".strip()
        chunks.append(chunk)

    return "\n\n".join(chunks)



def fallback_answer(city: str, query: str, places: List[Dict[str, Any]]) -> str:
    if not places:
        return f"No relevant places found for '{query}' in {city}."

    lines = [f"For '{query}' in {city}, here are the top matches:"]
    for p in places[:5]:
        name = p.get("name") or "Unknown place"
        category = p.get("category") or "N/A"
        line = f"- {name} ({category})"
        if p.get("wikipedia_summary"):
            line += f": {p['wikipedia_summary'][:150]}"
        lines.append(line)

    return "\n".join(lines)


def generate_answer(city: str, query: str, places: List[Dict[str, Any]]) -> str:
    print("[RAG] generate_answer started")

    if not places:
        return f"I could not find relevant attractions for '{query}' in {city}."

    try:
        context = build_context(places)

        user_prompt = f"""
City: {city}
User request: {query}

Context:
{context}

Respond with:
1. A short recommendation summary
2. A bullet list of top places with explanation
3. A short note on missing information if relevant
""".strip()

        client = get_openai_client()

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=60,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[RAG] LLM failed, using fallback: {e}")
        return fallback_answer(city, query, places)


def run_rag(city: str, query: str, top_k: int = 5):
    print("[RAG] run_rag started")
    places = retrieve_places(city, query, top_k)
    answer = generate_answer(city, query, places)

    return {
        "city": city,
        "query": query,
        "answer": answer,
        "retrieved_places": places,
        "grounded": True,
    }