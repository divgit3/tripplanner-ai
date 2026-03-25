import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_overpass_query(city: str) -> str:
    return f"""
    [out:json][timeout:60];
    area["name"="{city}"]->.searchArea;
    (
      node["tourism"](area.searchArea);
      way["tourism"](area.searchArea);
      relation["tourism"](area.searchArea);

      node["historic"](area.searchArea);
      way["historic"](area.searchArea);
      relation["historic"](area.searchArea);

      node["leisure"](area.searchArea);
      way["leisure"](area.searchArea);
      relation["leisure"](area.searchArea);

      node["natural"](area.searchArea);
      way["natural"](area.searchArea);
      relation["natural"](area.searchArea);

      node["amenity"](area.searchArea);
      way["amenity"](area.searchArea);
      relation["amenity"](area.searchArea);
    );
    out center tags;
    """


def fetch_osm_places(city: str) -> dict:
    query = build_overpass_query(city)
    response = requests.get(OVERPASS_URL, params={"data": query}, timeout=120)
    response.raise_for_status()
    return response.json()