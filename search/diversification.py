def diversify_results(reranked_results, max_per_category=2):
    diversified = []
    category_counts = {}

    for score, r in reranked_results:
        payload = r.payload if hasattr(r, "payload") else r.get("payload", {})
        category = (payload.get("category") or "").lower()

        count = category_counts.get(category, 0)

        if count >= max_per_category:
            continue

        diversified.append((score, r))
        category_counts[category] = count + 1

    return diversified