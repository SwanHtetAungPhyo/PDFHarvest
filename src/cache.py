"""
Simple JSON cache utilities for caching API responses.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


def sanitize_filename(s: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Parameters
    ----------
    s : str
        Input string (typically a DOI)
        
    Returns
    -------
    str
        Sanitized filename-safe string
    """
    s = s.strip().replace("doi:", "").replace("DOI:", "")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def cache_path(base: Path, namespace: str, doi: str) -> Path:
    """
    Generate cache file path for a DOI in a specific namespace.
    
    Parameters
    ----------
    base : Path
        Base output directory
    namespace : str
        Cache namespace (e.g., 'crossref', 'unpaywall', 'matches')
    doi : str
        DOI identifier
        
    Returns
    -------
    Path
        Path to cache file
    """
    return base / "cache" / namespace / f"{sanitize_filename(doi)}.json"


def read_cache_json(path: Path) -> Optional[Dict[str, Any]]:
    """
    Read JSON data from cache file.
    
    Parameters
    ----------
    path : Path
        Path to cache file
        
    Returns
    -------
    dict or None
        Cached data if file exists and is valid JSON, None otherwise
    """
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def write_cache_json(path: Path, data: Dict[str, Any]) -> None:
    """
    Write JSON data to cache file.
    
    Parameters
    ----------
    path : Path
        Path to cache file
    data : dict
        Data to cache
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
    except Exception as e:
        import logging
        logging.getLogger("harvest").warning(f"Cache write failed {path}: {e}")


def ensure_cache_dirs(base: Path) -> None:
    """
    Ensure all cache directories exist.
    
    Parameters
    ----------
    base : Path
        Base output directory
    """
    (base / "cache" / "crossref").mkdir(parents=True, exist_ok=True)
    (base / "cache" / "unpaywall").mkdir(parents=True, exist_ok=True)
    (base / "cache" / "matches").mkdir(parents=True, exist_ok=True)