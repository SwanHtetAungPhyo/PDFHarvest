"""
Tests for HTTP utilities.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.http import best_pdf_url, fetch_crossref, fetch_unpaywall


def test_best_pdf_url():
    """Test PDF URL extraction from Unpaywall data."""
    # Empty data
    assert best_pdf_url({}) is None
    assert best_pdf_url(None) is None

    # Best OA location with url_for_pdf
    ua_data = {
        "best_oa_location": {
            "url_for_pdf": "https://example.com/paper.pdf",
            "url": "https://example.com/paper",
        }
    }
    assert best_pdf_url(ua_data) == "https://example.com/paper.pdf"

    # Best OA location with only url
    ua_data = {"best_oa_location": {"url": "https://example.com/paper"}}
    assert best_pdf_url(ua_data) == "https://example.com/paper"

    # Fallback to oa_locations
    ua_data = {
        "oa_locations": [
            {"url": "https://example.com/paper1"},
            {"url_for_pdf": "https://example.com/paper2.pdf"},
        ]
    }
    assert best_pdf_url(ua_data) == "https://example.com/paper1"


@pytest.mark.asyncio
async def test_fetch_crossref():
    """Test Crossref API fetching."""
    # Mock client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "title": ["Test Paper"],
            "author": [{"given": "John", "family": "Doe"}],
        }
    }

    # Mock the backoff_request function
    with patch("src.http.backoff_request", new=AsyncMock(return_value=mock_response)):
        result = await fetch_crossref(mock_client, "10.1000/test")
        assert result["title"] == ["Test Paper"]
        assert len(result["author"]) == 1


@pytest.mark.asyncio
async def test_fetch_unpaywall():
    """Test Unpaywall API fetching."""
    # Mock client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "is_oa": True,
        "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"},
    }

    # Mock the backoff_request function
    with patch("src.http.backoff_request", new=AsyncMock(return_value=mock_response)):
        result = await fetch_unpaywall(mock_client, "10.1000/test", "test@example.com")
        assert result["is_oa"] is True
        assert "best_oa_location" in result
