"""
Main orchestrator for the batched DOI harvesting process.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

import httpx
import pandas as pd
from tqdm.asyncio import tqdm_asyncio

from .cache import cache_path, read_cache_json, write_cache_json, ensure_cache_dirs
from .config import Config, load_config
from .http import fetch_crossref, fetch_unpaywall, best_pdf_url, download_pdf
from .logging import setup_logging
from .pdfops import search_pdf, move_pdf_atomic


def ensure_dirs(base: Path, cfg: Config):
    """Ensure all required directories exist."""
    ensure_cache_dirs(base)
    # staging + final folders
    (base / cfg.folders.downloads).mkdir(parents=True, exist_ok=True)
    (base / cfg.folders.found).mkdir(parents=True, exist_ok=True)
    (base / cfg.folders.notfound).mkdir(parents=True, exist_ok=True)


async def prepare_one(
    doi: str, 
    cfg: Config, 
    api_client: httpx.AsyncClient, 
    pdf_client: httpx.AsyncClient,
    out_dir: Path
) -> Dict[str, Any]:
    """
    Stage 1 for a DOI:
      - Load or fetch Crossref + Unpaywall
      - If OA PDF URL exists, download to downloads/ (staging folder)
      - Return a record with: metadata, OA status, temp pdf path (if any)
    """
    log = logging.getLogger("harvest")
    cache_en = cfg.cache.enabled
    force_ref = cfg.cache.force_refresh
    downloads = out_dir / cfg.folders.downloads
    
    # cache files
    xref_cache = cache_path(out_dir, "crossref", doi)
    upw_cache = cache_path(out_dir, "unpaywall", doi)

    # cached?
    meta = read_cache_json(xref_cache) if (cache_en and not force_ref) else None
    oa = read_cache_json(upw_cache) if (cache_en and not force_ref) else None

    if meta is None:
        try:
            meta = await fetch_crossref(api_client, doi)
            if cache_en:
                write_cache_json(xref_cache, meta)
        except Exception:
            meta = {}
            
    if oa is None:
        try:
            oa = await fetch_unpaywall(api_client, doi, cfg.email)
            if cache_en:
                write_cache_json(upw_cache, oa)
        except Exception:
            oa = {}

    pdf_url = best_pdf_url(oa)
    temp_pdf = ""
    
    if pdf_url:
        # Always stage to downloads/ first
        from .cache import sanitize_filename
        fname = f"{sanitize_filename(doi)}.pdf"
        tgt = downloads / fname
        
        if tgt.exists() and not force_ref:
            temp_pdf = str(tgt)
        else:
            ok = await download_pdf(pdf_client, pdf_url, tgt)
            if ok:
                temp_pdf = str(tgt)

    # flatten some meta now
    title = "; ".join(meta.get("title", []) or [])
    journal = "; ".join(meta.get("container-title", []) or [])
    
    try:
        year = (meta.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
    except Exception:
        year = None
        
    authors = "; ".join(f"{a.get('given','')} {a.get('family','')}".strip()
                        for a in (meta.get("author", []) or []))

    row = {
        "doi": doi, 
        "title": title, 
        "journal": journal, 
        "year": year, 
        "authors": authors,
        "publisher": meta.get("publisher", ""), 
        "type": meta.get("type", ""),
        "crossref_url": meta.get("URL", ""),
        "is_oa": oa.get("is_oa", None),
        "oa_license": (oa.get("best_oa_location") or {}).get("license", None),
        "pdf_url": pdf_url or "",
        "pdf_temp_path": temp_pdf,      # staged location (downloads/)
        "pdf_final_path": "",           # will be set in stage 2
        "match_found": False, 
        "matched_strings": "", 
        "match_pages": "",
    }
    
    log.debug(f"Prepared {doi} | OA={row['is_oa']} | temp_pdf={bool(temp_pdf)}")
    return row


async def process_batch_pdfs(rows: List[Dict[str, Any]], cfg: Config, out_dir: Path):
    """
    For the batch's rows that have a staged PDF:
      - Search each PDF (thread executor)
      - Depending on hit, move the file to output_found/ or output_notfound/
      - Update rows in-place with match info & final path
      - Cache match results (so re-runs are fast)
    """
    log = logging.getLogger("harvest")
    needles = cfg.strings
    cache_en = cfg.cache.enabled
    force_ref = cfg.cache.force_refresh

    found_dir = out_dir / cfg.folders.found
    notfound_dir = out_dir / cfg.folders.notfound

    # Build tasks only for rows with a temp PDF and not cached match (unless force_refresh)
    to_process = []
    for r in rows:
        if not r.get("pdf_temp_path"):   # nothing to process
            continue
        m_cache = cache_path(out_dir, "matches", r["doi"])
        cached = read_cache_json(m_cache) if (cache_en and not force_ref) else None
        to_process.append((r, m_cache, cached))

    loop = asyncio.get_running_loop()
    # run PDF parsing concurrently in thread pool
    futs = []
    for r, m_cache, cached in to_process:
        if cached is not None:
            r["match_found"] = bool(cached.get("found"))
            r["matched_strings"] = ", ".join(cached.get("matches", []))
            r["match_pages"] = ", ".join(map(str, cached.get("pages", [])))
            continue
        futs.append(loop.run_in_executor(None, search_pdf, Path(r["pdf_temp_path"]), needles))

    # collect fresh parsing results in the same order
    idx = 0
    for r, m_cache, cached in to_process:
        if cached is not None:
            # will move below based on cached result
            pass
        else:
            res = await futs[idx]
            idx += 1
            r["match_found"] = bool(res.get("found"))
            r["matched_strings"] = ", ".join(res.get("matches", []))
            r["match_pages"] = ", ".join(map(str, res.get("pages", [])))
            if cache_en:
                write_cache_json(m_cache, res)

        # move the staged file according to match flag
        src = Path(r["pdf_temp_path"])
        if not src.exists():
            continue  # might have been moved already on a previous run
            
        dest_dir = found_dir if r["match_found"] else notfound_dir
        final_path = move_pdf_atomic(src, dest_dir)
        r["pdf_final_path"] = str(final_path)
        # wipe temp path so re-runs won't try to move again
        r["pdf_temp_path"] = ""
        
        log.debug(f"Routed {r['doi']} → {'FOUND' if r['match_found'] else 'NOTFOUND'} | {final_path.name}")


async def run(cfg_path: str) -> pd.DataFrame:
    """
    Batch orchestrator:
      - Read config + Excel DOIs
      - For DOIs in chunks of batch_size:
          * Stage 1: concurrently prepare (metadata+OA) and download PDFs into downloads/
          * Stage 2: pause downloading; process batch PDFs and move to final folders
      - Append results and write report.xlsx/.csv at the end (and optionally after each batch)
    """
    cfg = load_config(cfg_path)
    out_dir = Path(cfg.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_dirs(out_dir, cfg)

    log = setup_logging(cfg.to_dict(), out_dir)
    log.info("Starting batched DOI harvest")

    # input
    df = pd.read_excel(cfg.input_excel)
    doi_col = cfg.doi_column
    
    if doi_col not in df.columns:
        raise ValueError(f"Excel must contain column '{doi_col}'")
        
    dois = [str(x).strip() for x in df[doi_col].dropna().tolist()]
    log.info(f"Loaded {len(dois)} DOIs")

    # HTTP clients (kept open across batches)
    headers = {"User-Agent": cfg.http.user_agent}
    limits = httpx.Limits(
        max_keepalive_connections=cfg.http.max_keepalive,
        max_connections=cfg.http.max_connections,
    )
    timeout = httpx.Timeout(
        cfg.timeouts.read,
        connect=cfg.timeouts.connect
    )
    
    batch_size = cfg.batch_size
    # polite parallelism *within a batch* (metadata+downloads)
    per_batch_concurrency = cfg.concurrency

    all_rows: List[Dict[str, Any]] = []
    
    async with httpx.AsyncClient(headers=headers, limits=limits, timeout=timeout, http2=False) as api_client, \
               httpx.AsyncClient(headers=headers, limits=limits, timeout=timeout, http2=False) as pdf_client:

        for start in range(0, len(dois), batch_size):
            chunk = dois[start:start + batch_size]
            log.info(f"Batch {start//batch_size + 1}: preparing {len(chunk)} DOIs")
            sem = asyncio.Semaphore(per_batch_concurrency)

            # ------ Stage 1: prepare+download (bounded concurrency), staged into downloads/ ------
            async def prep_wrapped(doi):
                async with sem:
                    return await prepare_one(doi, cfg, api_client, pdf_client, out_dir)

            prep_tasks = [prep_wrapped(doi) for doi in chunk]
            rows = await tqdm_asyncio.gather(*prep_tasks, total=len(prep_tasks), desc="Stage 1: prepare+download")

            # ------ Stage 2: processing (no network; only CPU and file moves) ------
            log.info(f"Batch {start//batch_size + 1}: processing PDFs")
            await process_batch_pdfs(rows, cfg, out_dir)

            all_rows.extend(rows)

            # optional: write incremental report after each batch
            if cfg.write_after_each_batch:
                out_df = pd.DataFrame(all_rows)
                out_df.to_excel(out_dir / "report.xlsx", index=False)
                out_df.to_csv(out_dir / "report.csv", index=False, encoding="utf-8")
                log.info(f"Incremental report written: {len(out_df)} rows")

    # final report
    out_df = pd.DataFrame(all_rows)
    out_df.to_excel(out_dir / "report.xlsx", index=False)
    out_df.to_csv(out_dir / "report.csv", index=False, encoding="utf-8")
    log.info(f"Done. Total rows: {len(out_df)} → {out_dir/'report.xlsx'}")
    return out_df