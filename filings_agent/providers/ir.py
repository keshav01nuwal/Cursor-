from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from ..http_client import HttpClient
from ..classifiers import classify_from_title


@dataclass
class IrDoc:
    title: str
    url: str
    published_date: Optional[str]
    doctype: Optional[str]


COMMON_IR_PATHS = [
    "/investors",
    "/investor-relations",
    "/ir",
    "/company/investors",
]


class IRProvider:
    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def discover(self, base_url: str, max_docs: int = 50) -> List[IrDoc]:
        docs: List[IrDoc] = []
        for path in COMMON_IR_PATHS:
            try:
                url = urljoin(base_url, path)
                resp = self.http.get(url)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href")
                    text = (a.get_text() or "").strip()
                    if not href or not text:
                        continue
                    abs_url = urljoin(url, href)
                    doctype = classify_from_title(text)
                    if doctype:
                        docs.append(IrDoc(title=text, url=abs_url, published_date=None, doctype=doctype))
                        if len(docs) >= max_docs:
                            return docs
            except Exception:
                continue
        return docs