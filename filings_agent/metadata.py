from __future__ import annotations

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
import json
import csv
from pathlib import Path


class MetadataRow(BaseModel):
    company: str
    ticker: str
    market: Optional[str] = None
    cik: Optional[str] = None
    year: int
    period: Optional[str] = None
    doctype: str
    title: str
    local_path: str
    source_url: str
    source_domain: str
    published_date: str
    size: int
    sha256: str
    source_type: str
    status: str = Field(default="saved")


def write_metadata(paths_root: Path, rows: List[MetadataRow]) -> None:
    json_path = paths_root / "metadata.json"
    csv_path = paths_root / "metadata.csv"
    json_path.write_text(json.dumps([r.model_dump() for r in rows], indent=2))

    fieldnames = list(MetadataRow.model_fields.keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r.model_dump())


def summarize_counts(rows: List[MetadataRow]) -> Dict[int, Dict[str, int]]:
    counts: Dict[int, Dict[str, int]] = {}
    for r in rows:
        counts.setdefault(r.year, {})
        counts[r.year][r.doctype] = counts[r.year].get(r.doctype, 0) + 1
    return counts