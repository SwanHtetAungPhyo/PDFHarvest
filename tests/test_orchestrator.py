"""
Tests for the main orchestrator.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.config import Config
from src.orchestrator import ensure_dirs


def test_ensure_dirs():
    """Test directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        config = Config(
            input_excel="test.xlsx", email="test@example.com", strings=["test"]
        )

        ensure_dirs(base, config)

        # Check cache directories
        assert (base / "cache" / "crossref").exists()
        assert (base / "cache" / "unpaywall").exists()
        assert (base / "cache" / "matches").exists()

        # Check output directories
        assert (base / "downloads").exists()
        assert (base / "output_found").exists()
        assert (base / "output_notfound").exists()


@pytest.mark.asyncio
async def test_prepare_one():
    """Test single DOI preparation."""
    from src.orchestrator import prepare_one

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        config = Config(
            input_excel="test.xlsx", email="test@example.com", strings=["test"]
        )

        # Mock clients
        api_client = AsyncMock()
        pdf_client = AsyncMock()

        # Mock the fetch functions
        with patch("src.orchestrator.fetch_crossref") as mock_crossref, patch(
            "src.orchestrator.fetch_unpaywall"
        ) as mock_unpaywall, patch("src.orchestrator.best_pdf_url") as mock_best_pdf:

            mock_crossref.return_value = {
                "title": ["Test Paper"],
                "author": [{"given": "John", "family": "Doe"}],
                "publisher": "Test Publisher",
            }
            mock_unpaywall.return_value = {"is_oa": True}
            mock_best_pdf.return_value = None  # No PDF URL

            result = await prepare_one(
                "10.1000/test", config, api_client, pdf_client, out_dir
            )

            assert result["doi"] == "10.1000/test"
            assert result["title"] == "Test Paper"
            assert result["publisher"] == "Test Publisher"
            assert result["is_oa"] is True
            assert result["pdf_temp_path"] == ""  # No PDF downloaded
