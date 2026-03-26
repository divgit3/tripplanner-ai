import re


def filter_places(places: list[dict]) -> list[dict]:
    filtered = []

    for p in places:
        name = (p.get("name") or "").lower()
        summary = (p.get("summary") or "").lower()

        if not name or len(name) < 3:
            continue

        if "park" in name and not summary:
            continue

        filtered.append(p)

    return filtered


def is_close(lat1, lon1, lat2, lon2, threshold=0.01):
    if any(v is None for v in [lat1, lon1, lat2, lon2]):
        return False
    return abs(lat1 - lat2) < threshold and abs(lon1 - lon2) < threshold


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)

    stopwords = {"the", "at", "of", "and"}
    tokens = [t for t in name.split() if t not in stopwords]

    return " ".join(tokens)


def get_payload(result):
    return result.payload if hasattr(result, "payload") else result.get("payload", {})



def deduplicate_results(results):
    deduped = []

    for r in results:
        payload = get_payload(r)

        name = normalize_name(payload.get("name") or "")

        is_duplicate = False

        for existing in deduped:
            existing_payload = get_payload(existing)
            existing_name = normalize_name(existing_payload.get("name") or "")

            if name and name == existing_name:
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(r)

    return deduped



# def deduplicate_results(results):
#     deduped = []

#     for r in results:
#         payload = get_payload(r)

#         name = normalize_name(payload.get("name") or "")
#         lat = payload.get("lat")
#         lon = payload.get("lon")

#         is_duplicate = False

#         for existing in deduped:
#             existing_payload = get_payload(existing)

#             existing_name = normalize_name(existing_payload.get("name") or "")
#             existing_lat = existing_payload.get("lat")
#             existing_lon = existing_payload.get("lon")

#             # Safer duplicate rule:
#             # same normalized name
#             # OR same normalized name + close location
#             if name and name == existing_name:
#                 is_duplicate = True
#                 break

#             if (
#                 name
#                 and existing_name
#                 and name == existing_name
#                 and is_close(lat, lon, existing_lat, existing_lon)
#             ):
#                 is_duplicate = True
#                 break

#         if not is_duplicate:
#             deduped.append(r)

#     return deduped