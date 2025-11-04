"""
HTTP utilities for DOI harvesting.

Responsibilities:
- Resilient HTTP requests with retries/backoff
- API-specific helpers for Crossref and Unpaywall
- Streaming PDF downloads

This module is by design simple and stateless. Stateful concerns
(connection pools, timeouts, HTTP/2) are configured by callers via an
'httpx.AsyncClient' instance.
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

# Base API endpoints (kept here so they're easy to test/override)
CROSSREF = "https://api.crossref.org/works/"
UNPAYWALL = "https://api.unpaywall.org/v2/"


async def backoff_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """
    Perform an HTTP request with retry + exponential backoff for transient errors.

    Retries on:
        - 429 Too Many Requests   (honors 'Retry-After' if present)
        - 500, 502, 503, 504      (common transient server errors)

    Strategy:
        - Up to `max_tries` attempts.
        - If 'Retry-After' header is present, sleep that many seconds.
        - Otherwise, exponential backoff: base * (2**i), capped (here at 10s).

    Parameters
    ----------
    client : httpx.AsyncClient
        Preconfigured client (headers, limits, timeouts, http2) supplied by caller.
    method : str
        "GET", "POST", etc.
    url : str
        Absolute URL to request.
    **kwargs :
        Passed through to 'client.request' (params, json, timeout, etc.).

    Returns
    -------
    httpx.Response
        Response on success; raises for non-retriable errors or after final failure.
    """
    log = logging.getLogger("harvest")
    max_tries = 6            # total attempts
    base = 0.5               # base backoff in seconds
    cap = 10.0               # max sleep between retries

    for i in range(max_tries):
        try:
            r = await client.request(method, url, **kwargs)

            # Transient conditions we want to retry
            if r.status_code in (429, 500, 502, 503, 504):
                # Prefer server-provided wait time
                ra = r.headers.get("Retry-After")
                if ra is not None:
                    try:
                        wait = float(ra)
                    except ValueError:
                        wait = min(base * (2 ** i), cap)
                else:
                    wait = min(base * (2 ** i), cap)

                log.warning(
                    f"{r.status_code} {url} → backoff {wait:.2f}s (try {i+1}/{max_tries})"
                )
                await asyncio.sleep(wait)
                continue

            # Raise for non-2xx/3xx (client errors, etc.)
            r.raise_for_status()
            return r

        except httpx.HTTPError as e:
            # Network/connect or HTTP protocol errors
            if i == max_tries - 1:
                log.error(f"HTTP error {url}: {e}")
                raise
            # Backoff for transport-layer issues as well
            wait = min(base * (2 ** i), cap)
            log.warning(f"Transport error {url}: {e} → retry in {wait:.2f}s")
            await asyncio.sleep(wait)

    # There are dragons... we should never end up here...
    raise RuntimeError("backoff_request exhausted retries unexpectedly")


async def fetch_crossref(client: httpx.AsyncClient, doi: str) -> Dict[str, Any]:
    """
    Fetch Crossref 'works' metadata for a DOI.

    Endpoint:
        GET https://api.crossref.org/works/<doi>

    Returns
    -------
    dict
        The 'message' field from Crossref JSON, or {} on unexpected shapes.
    """
    # DOI must be URL-encoded to be safe in the path
    url = CROSSREF + urllib.parse.quote(doi, safe="")
    # Crossref can be slow; pass a per-request timeout if needed (overrides client default)
    r = await backoff_request(client, "GET", url, timeout=20)
    data = r.json()
    # Crossref wraps actual content in 'message'
    return data.get("message", {}) if isinstance(data, dict) else {}


async def fetch_unpaywall(client: httpx.AsyncClient, doi: str, email: str) -> Dict[str, Any]:
    """
    Fetch Unpaywall record for a DOI.
    
    Endpoint:
        GET https://api.unpaywall.org/v2/<doi>?email=<your_email>

    Notes
    -----
    - Unpaywall requires an email parameter for fair-use and contact.
    - We treat 404 as "no record" and return {} (not an error).

    Returns
    -------
    dict
        The full Unpaywall JSON object, or {} for 404 / unexpected shapes.
    """
    url = UNPAYWALL + urllib.parse.quote(doi, safe="")
    # Provide the required email as a query parameter
    r = await backoff_request(client, "GET", url, params={"email": email}, timeout=20)

    # If Unpaywall has no record, it responds 404. backoff_request would have raised,
    # and we explicitly re-check status here only if the server returned a body w/ 404.
    if r.status_code == 404:
        return {}

    # Typical success: JSON payload
    try:
        return r.json()
    except ValueError:
        # Unexpected non-JSON body; treat as missing
        return {}


def best_pdf_url(ua: Dict[str, Any]) -> Optional[str]:
    """
    Extract the "best" OA PDF URL from an Unpaywall record.

    Preference order:
        1) best_oa_location.url_for_pdf
        2) best_oa_location.url
        3) first match from oa_locations[*].url_for_pdf
        4) first match from oa_locations[*].url

    Returns
    -------
    str | None
        A direct (or near-direct) PDF URL if found; else None.
    """
    if not ua:
        return None

    # Primary best-oa fields
    loc = ua.get("best_oa_location") or {}
    pdf = loc.get("url_for_pdf") or loc.get("url")
    if pdf:
        return pdf

    # Fallback to any OA location
    for loc in ua.get("oa_locations") or []:
        pdf = loc.get("url_for_pdf") or loc.get("url")
        if pdf:
            return pdf

    return None


async def download_pdf(
    client: httpx.AsyncClient,
    url: str,
    out_path: Path,
) -> bool:
    """
    Stream a PDF from `url` to `out_path` with basic validation.

    Steps:
        - Issue a streaming GET.
        - Write chunks to disk (parents created as needed).
        - Validate file header begins with b'%PDF' (simple sanity check).
        - Return True on success; False if status >= 400, invalid header, or exceptions.

    Notes
    -----
    - This function trusts the URL: it does not enforce a max size nor confirm
      Content-Type. Consider adding safeguards for production.
    - Caller provides the client (so connection pooling, http2, and timeouts are shared).
    """
    log = logging.getLogger("harvest")

    try:
        # Stream the response so we don't buffer entire file in memory
        async with client.stream("GET", url, timeout=40) as r:
            if r.status_code >= 400:
                log.warning(f"PDF {url} → HTTP {r.status_code}")
                return False

            # Ensure destination directory exists
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # Write chunks as they arrive
            with open(out_path, "wb") as f:
                async for chunk in r.iter_bytes():
                    # Some servers may send keep-alive chunks; skip empties
                    if chunk:
                        f.write(chunk)

        # Check the PDF magic header, we do not want to check too much
        with open(out_path, "rb") as f:
            if f.read(4) != b"%PDF":
                log.warning(f"Not a PDF (magic header mismatch) → {url}")
                # Remove the invalid file to keep the workspace clean
                out_path.unlink(missing_ok=True)
                return False

        return True

    except Exception as e:
        # Network errors, file system errors, etc.
        log.warning(f"PDF download failed {url}: {e}")
        return False