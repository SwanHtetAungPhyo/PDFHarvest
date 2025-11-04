"""
Tests for PDF operations.
"""

import tempfile
from pathlib import Path

from pdfops import search_pdf, move_pdf_atomic


def test_move_pdf_atomic():
    """Test atomic PDF file moving with collision handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create source file
        src = tmpdir / "source.pdf"
        src.write_text("test content")
        
        # Create destination directory
        dst_dir = tmpdir / "destination"
        
        # First move should work normally
        result1 = move_pdf_atomic(src, dst_dir)
        assert result1 == dst_dir / "source.pdf"
        assert result1.exists()
        assert result1.read_text() == "test content"
        
        # Create another source file with same name
        src2 = tmpdir / "source.pdf"
        src2.write_text("test content 2")
        
        # Second move should append counter
        result2 = move_pdf_atomic(src2, dst_dir)
        assert result2 == dst_dir / "source_1.pdf"
        assert result2.exists()
        assert result2.read_text() == "test content 2"
        
        # Original file should still exist
        assert result1.exists()
        assert result1.read_text() == "test content"


def test_search_pdf_no_file():
    """Test PDF search with non-existent file."""
    non_existent = Path("/tmp/does_not_exist.pdf")
    result = search_pdf(non_existent, ["test"])
    
    assert result["found"] is False
    assert result["matches"] == []
    assert result["pages"] == []