"""
PDF processing operations: text search and file management.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from pypdf import PdfReader


def search_pdf(pdf_path: Path, needles: List[str]) -> Dict[str, Any]:
    """
    Text search (casefolded substrings) in PDF content.
    
    If you need OCR later, add an opt-in pass here.

    Parameters
    ----------
    pdf_path : Path
        Path to PDF file to search
    needles : List[str]
        List of strings to search for (case-insensitive)

    Returns
    -------
    dict
        Dictionary with keys:
        - found: bool, whether any matches were found
        - matches: list of matched strings
        - pages: list of page numbers where matches were found
    """
    res = {"found": False, "matches": [], "pages": []}
    
    try:
        reader = PdfReader(str(pdf_path))
        ns = [n.casefold() for n in needles]
        hits, pages = set(), set()
        
        for i, p in enumerate(reader.pages):
            try:
                txt = (p.extract_text() or "").casefold()
            except Exception:
                txt = ""
            
            if not txt:
                continue
                
            page_hit = False
            for n in ns:
                if n in txt:
                    hits.add(n)
                    page_hit = True
                    
            if page_hit:
                pages.add(i + 1)
                
        if hits:
            res.update(found=True, matches=sorted(hits), pages=sorted(pages))
            
    except Exception as e:
        logging.getLogger("harvest").warning(f"PDF parse failed {pdf_path}: {e}")
        
    return res


def move_pdf_atomic(src: Path, dst_dir: Path) -> Path:
    """
    Move a file atomically, preserving name; if collision, append a counter.

    Parameters
    ----------
    src : Path
        Source file path
    dst_dir : Path
        Destination directory

    Returns
    -------
    Path
        Final path where file was moved
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    
    if not target.exists():
        return src.replace(target)
        
    stem, suf = src.stem, src.suffix
    k = 1
    while True:
        cand = dst_dir / f"{stem}_{k}{suf}"
        if not cand.exists():
            return src.replace(cand)
        k += 1