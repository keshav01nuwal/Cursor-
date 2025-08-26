from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple


def sanitize_filename(name: str, max_length: int = 80) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned or "document"


def build_company_root(out_root: str, company: str) -> Path:
    safe_company = sanitize_filename(company, max_length=120)
    root = Path(out_root) / safe_company
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_doc_path(company_root: Path, year: int, doc_type: str, date_str: str, short_title: str, ext: str) -> Path:
    folder = company_root / f"{year}" / doc_type
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{date_str}__{doc_type}__{sanitize_filename(short_title)}{ext}"
    return folder / filename


def guess_extension_from_url(url: str) -> str:
    lower = url.lower()
    for ext in [".pdf", ".xlsx", ".xls", ".csv", ".htm", ".html", ".txt"]:
        if lower.endswith(ext):
            return ext
    return ".html"