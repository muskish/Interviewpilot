"""
Unit tests for Autonomous Web Search Verification Service.
"""
from __future__ import annotations

from unittest.mock import patch

from services.search_service import search_web


def test_search_web_empty():
    """Verify empty query returns empty string."""
    assert search_web("") == ""
    assert search_web(None) == ""


@patch("services.search_service.DDGS")
def test_search_web_success(mock_ddgs_cls):
    """Verify search returns formatted markdown snippets."""
    mock_ddgs_instance = mock_ddgs_cls.return_value.__enter__.return_value
    mock_ddgs_instance.text.return_value = [
        {
            "title": "Python 3.13 Released",
            "body": "Python 3.13 includes a free-threaded build without the GIL.",
            "href": "https://python.org",
        }
    ]

    result = search_web("Python 3.13 GIL")
    assert "Python 3.13 Released" in result
    assert "without the GIL" in result
    assert "https://python.org" in result
