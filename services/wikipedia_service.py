from __future__ import annotations
from difflib import SequenceMatcher
import time
from typing import Optional, Dict
from urllib.parse import quote

import requests


WIKIPEDIA_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
SEARCH_API = "https://en.wikipedia.org/w/api.php"


class WikipediaService:

    def __init__(self, sleep_seconds: float = 0.2, timeout: int = 10):
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "tripplanner-ai/1.0 (educational project)"
        })


    def is_reasonable_match(self, place_name: str, wiki_title: str, threshold: float = 0.60) -> bool:
        a = (place_name or "").lower().strip()
        b = (wiki_title or "").lower().strip()

        score = SequenceMatcher(None, a, b).ratio()
        return score >= threshold



    def get_summary_by_title(self, title: str) -> Optional[Dict]:
        """
        Fetch Wikipedia summary for an exact title.
        """

        if not title:
            return None

        url = WIKIPEDIA_SUMMARY_API.format(quote(title, safe=""))

        try:
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                return None

            data = response.json()

            if data.get("type") == "disambiguation":
                return None

            summary = data.get("extract")
            page_title = data.get("title")

            content_urls = data.get("content_urls", {})
            desktop = content_urls.get("desktop", {})
            page_url = desktop.get("page")

            if not summary or not page_title:
                return None

            time.sleep(self.sleep_seconds)

            return {
                "title": page_title,
                "summary": summary,
                "url": page_url
            }

        except requests.RequestException:
            return None


    def search_title(self, query: str) -> Optional[str]:
        """
        Search Wikipedia and return the best title match.
        """

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 5
        }

        try:
            response = self.session.get(SEARCH_API, params=params, timeout=self.timeout)

            if response.status_code != 200:
                return None

            data = response.json()

            results = data.get("query", {}).get("search", [])

            if not results:
                return None

            return results[0].get("title")

        except requests.RequestException:
            return None


    def enrich_place(self, name: str, city: str | None = None, state: str | None = None):
        if not name:
            return None

        # 1. exact title
        exact = self.get_summary_by_title(name)
        if exact and self.is_location_relevant(exact, city=city, state=state):
            return exact

        # 2. search with city/state context
        query_parts = [name]
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)

        query = ", ".join(query_parts)
        matched_title = self.search_title(query)

        if matched_title and self.is_reasonable_match(name, matched_title):
            result = self.get_summary_by_title(matched_title)
            if result and self.is_location_relevant(result, city=city, state=state):
                return result

        # 3. plain search fallback
        matched_title = self.search_title(name)
        if matched_title and self.is_reasonable_match(name, matched_title):
            result = self.get_summary_by_title(matched_title)
            if result and self.is_location_relevant(result, city=city, state=state):
                return result

        return None

    def is_location_relevant(self, result: dict, city: str | None = None, state: str | None = None) -> bool:
        text = " ".join([
            result.get("title", "") or "",
            result.get("summary", "") or "",
            result.get("url", "") or "",
        ]).lower()

        allowed_terms = set()

        if city:
            allowed_terms.add(city.lower())

        if state:
            allowed_terms.add(state.lower())

        # useful synonyms for this project
        if city and city.lower() == "tampa":
            allowed_terms.update({"tampa bay", "hillsborough county"})
        if state and state.lower() == "florida":
            allowed_terms.update({"fl", "florida"})

        return any(term in text for term in allowed_terms)