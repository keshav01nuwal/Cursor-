from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse

from .http_client import HttpClient, compute_sha256
from .providers.sec import SecProvider, SecFiling
from .providers.ir import IRProvider, IrDoc
from .metadata import MetadataRow, write_metadata, summarize_counts
from .output import build_company_root, build_doc_path, guess_extension_from_url
from .classifiers import classify_from_sec_form


def _setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("filings_agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(log_path)
    sh = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def run_agent(
    *,
    company_ticker: str,
    company_name: Optional[str],
    country: Optional[str],
    market: Optional[str],
    max_years: int,
    out_root: str,
    ir_only: bool,
    reg_only: bool,
    user_agent: str,
    max_concurrency: int,
    log_file: str,
) -> None:
    # Initialize HTTP client
    http = HttpClient(user_agent=user_agent)

    # SEC provider used both for resolution and regulator fallback
    sec = SecProvider(http)

    # Resolve company via SEC when US ticker or when unspecified
    resolved = sec.resolve_company(company_ticker)
    if not resolved:
        print(f"Could not resolve ticker {company_ticker}")
        return

    cik_str = str(resolved.get("cik_str"))
    resolved_company_name = company_name or resolved.get("title") or company_ticker

    # Determine market
    primary_market = market or sec.get_primary_market(company_ticker) or country or "US"

    # Prepare output roots and logger
    company_root = build_company_root(out_root, resolved_company_name)
    log_path = company_root / log_file
    logger = _setup_logger(log_path)
    logger.info("Run started for %s (%s)", resolved_company_name, company_ticker)

    rows: List[MetadataRow] = []
    seen_hashes: set[str] = set()

    def download_and_record(url: str, *, doctype: str, title: str, date_str: str, year: int, source_type: str, cik: Optional[str] = None) -> Optional[MetadataRow]:
        try:
            resp = http.get(url, stream=True)
            if resp.status_code != 200:
                logger.warning("Failed to download %s (%s)", url, resp.status_code)
                return None
            content = resp.content
            digest = compute_sha256(content)
            if digest in seen_hashes:
                logger.info("Duplicate skipped (hash): %s", url)
                return None
            seen_hashes.add(digest)
            ext = guess_extension_from_url(url)
            path = build_doc_path(company_root, year, doctype, date_str.replace("-", ""), title, ext)
            path.write_bytes(content)
            parsed = urlparse(url)
            row = MetadataRow(
                company=resolved_company_name,
                ticker=company_ticker,
                market=primary_market,
                cik=cik,
                year=year,
                period=None,
                doctype=doctype,
                title=title,
                local_path=str(path),
                source_url=url,
                source_domain=parsed.netloc,
                published_date=date_str,
                size=len(content),
                sha256=digest,
                source_type=source_type,
                status="saved",
            )
            return row
        except Exception as e:
            logger.exception("Error downloading %s: %s", url, e)
            return None

    # Collect from SEC unless ir_only
    tasks: List[Tuple[str, Dict]] = []
    if not ir_only:
        logger.info("Fetching SEC filings for last %d years", max_years)
        sec_filings: List[SecFiling] = sec.list_filings_last_n_years(company_ticker, max_years)
        for f in sec_filings:
            doctype = classify_from_sec_form(f.form)
            if not doctype:
                continue
            tasks.append((f.url, {"doctype": doctype, "title": f.form, "date_str": f.filing_date, "year": int(f.filing_date[:4]), "source_type": "SEC", "cik": f.cik}))

    # IR provider if not reg_only and if IR domain is known (not implemented discovery here)
    if not reg_only:
        ir = IRProvider(http)
        # If user provided a company_name and a likely domain was known, we could probe it.
        # For now, skip automatic IR probing unless country is not US and market is not provided.
        # This block is intentionally conservative and acts as a stub for future enhancement.
        logger.info("IR discovery skipped unless explicit domain is provided (not implemented)")

    # Execute downloads concurrently
    results: List[Optional[MetadataRow]] = []
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        futures = [pool.submit(download_and_record, url, **kwargs) for url, kwargs in tasks]
        for fut in as_completed(futures):
            results.append(fut.result())

    # Filter successful
    rows = [r for r in results if r is not None]

    # Write metadata files
    write_metadata(company_root, rows)

    # Print counts
    counts = summarize_counts(rows)
    for year, by_type in sorted(counts.items()):
        for dtype, n in sorted(by_type.items()):
            print(f"{year} {dtype}: {n}")
    print(f"Output root: {company_root}")
    logger.info("Completed with %d documents saved", len(rows))