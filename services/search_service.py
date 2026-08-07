"""
Autonomous Web Search Verification Tool using DuckDuckGo.

Enables agents to query live web search results for fact-checking candidate claims,
framework versions, and technical concepts. Completely free with zero API keys required.
"""
from __future__ import annotations

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from utils.logger import get_logger

logger = get_logger(__name__)


def search_web(query: str, max_results: int = 3) -> str:
    """
    Perform a live web search using DuckDuckGo and return formatted snippet results.
    Returns empty string if query fails or yields no results.
    """
    if not query or not query.strip():
        return ""

    clean_query = query.strip()
    logger.info("SearchService: Executing live web search for query: %r", clean_query)

    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(clean_query, max_results=max_results))
            for item in raw_results:
                title = item.get("title", "No Title")
                body = item.get("body", "No Snippet")
                url = item.get("href", "")
                results.append(f"• Title: {title}\n  Snippet: {body}\n  Source: {url}")

        if not results:
            return "No web search results found."

        return "\n\n".join(results)

    except Exception as exc:
        logger.error("SearchService: Web search failed for query %r: %s", clean_query, exc)
        return ""
