"""
Web Grounding — fetches real-time context before LLM calls.

"""

import re
import urllib.parse
import requests
from typing import Optional

from backend.core.logger import log

# Keywords that signal real-time / current data is needed
_REALTIME_SIGNALS = [
    "latest", "current", "today", "now", "recent", "score",
    "goal", "goals", "match", "game", "win", "won", "lost",
    "2024", "2025", "2026", "this year", "last year",
    "how many", "total", "count", "number of",
    "price", "stock", "weather", "news", "update",
]


def needs_grounding(prompt: str) -> bool:
    """Return True if the prompt likely needs real-time context."""
    lower = prompt.lower()
    return any(signal in lower for signal in _REALTIME_SIGNALS)


def fetch_grounding_context(prompt: str, max_chars: int = 1500) -> Optional[str]:
    """
    Search Wikipedia for context relevant to the prompt.
    Returns a text snippet to inject as system context, or None on failure.
    """
    try:
        # Extract search query from prompt (remove question words)
        query = _clean_query(prompt)
        log.info(f"Fetching grounding context for: {query[:60]}")

        # Step 1: Search Wikipedia for relevant article
        search_url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={urllib.parse.quote(query)}"
            "&format=json&srlimit=1&utf8=1"
        )
        resp = requests.get(
            search_url,
            timeout=8,
            headers={"User-Agent": "LLMObservatory/1.0 (educational project)"},
        )
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])

        if not results:
            log.warning("No Wikipedia results found for grounding")
            return None

        title = results[0]["title"]

        # Step 2: Fetch article summary
        summary_url = (
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        )
        resp2 = requests.get(
            summary_url,
            timeout=8,
            headers={"User-Agent": "LLMObservatory/1.0 (educational project)"},
        )
        resp2.raise_for_status()
        data    = resp2.json()
        extract = data.get("extract", "")

        if not extract:
            return None

        context = (
            f"[Web context from Wikipedia — '{title}']\n"
            f"{extract[:max_chars]}"
        )
        log.info(f"Grounding context fetched: {len(extract)} chars from '{title}'")
        return context

    except Exception as e:
        log.warning(f"Grounding fetch failed (non-critical): {e}")
        return None


def _clean_query(prompt: str) -> str:
    """Strip question words and punctuation for a cleaner search query."""
    stop = ["what is", "what are", "who is", "tell me", "explain",
            "how many", "how much", "when did", "where is", "?", "please"]
    q = prompt.lower()
    for s in stop:
        q = q.replace(s, " ")
    return re.sub(r"\s+", " ", q).strip()