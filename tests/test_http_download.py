"""
Tests for HTTP PDF download functionality with redirect handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.http import download_pdf


@pytest.mark.asyncio
async def test_download_pdf_success():
    """Test successful PDF download."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client with successful response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}

        # Create an async iterator for chunks with PDF header
        pdf_content = b"%PDF-1.4\n%Test PDF content here"

        async def mock_aiter_bytes():
            yield pdf_content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/test.pdf", out_path
        )

        assert result is True
        assert out_path.exists()
        with open(out_path, "rb") as f:
            content = f.read()
            assert content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_download_pdf_http_error():
    """Test PDF download with HTTP error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client with error response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/notfound.pdf", out_path
        )

        assert result is False
        assert not out_path.exists()


@pytest.mark.asyncio
async def test_download_pdf_html_content():
    """Test PDF download that returns HTML instead of PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client with HTML response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        # Create an async iterator for HTML chunks
        html_content = b"<html><body>This is a landing page</body></html>"

        async def mock_aiter_bytes():
            yield html_content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/landing.html", out_path
        )

        assert result is False


@pytest.mark.asyncio
async def test_download_pdf_invalid_header():
    """Test PDF download with invalid PDF header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client with response that has wrong content
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}

        # Create an async iterator with non-PDF content
        fake_content = b"This is not a PDF file"

        async def mock_aiter_bytes():
            yield fake_content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/fake.pdf", out_path
        )

        assert result is False
        # File might still exist on Windows due to file locking, but result should be False


@pytest.mark.asyncio
async def test_download_pdf_with_redirects():
    """Test that follow_redirects parameter is used."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}

        pdf_content = b"%PDF-1.4\n%Redirected PDF"

        async def mock_aiter_bytes():
            yield pdf_content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/redirect.pdf", out_path
        )

        # Verify that stream was called with follow_redirects=True
        mock_client.stream.assert_called_once()
        call_kwargs = mock_client.stream.call_args[1]
        assert call_kwargs.get("follow_redirects") is True

        assert result is True


@pytest.mark.asyncio
async def test_download_pdf_mismatched_content_type():
    """Test PDF download where content-type says HTML but content is actually PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test.pdf"

        # Mock client with HTML content-type but PDF content
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}

        # Create an async iterator with actual PDF content
        pdf_content = b"%PDF-1.4\n%This is actually a PDF despite HTML header"

        async def mock_aiter_bytes():
            # Return content in chunks
            yield pdf_content[:10]  # First chunk with PDF magic
            yield pdf_content[10:]  # Rest of content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream)

        result = await download_pdf(
            mock_client, "https://example.com/weird.pdf", out_path
        )

        # Should detect it's actually a PDF and download successfully
        assert result is True
        assert out_path.exists()
        with open(out_path, "rb") as f:
            content = f.read()
            assert content.startswith(b"%PDF")
