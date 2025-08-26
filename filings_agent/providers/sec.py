from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse

from ..http_client import HttpClient
from ..classifiers import classify_from_sec_form


@dataclass
class SecFiling:
    form: str
    filing_date: str
    report_date: Optional[str]
    primary_doc: str
    accession_no: str
    cik: str
    company_name: str
    url: str


class SecProvider:
    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self._ticker_cache: Optional[Dict[str, Dict]] = None
        self._ticker_exchange_cache: Optional[Dict[str, Dict]] = None

    def _load_tickers(self) -> None:
        if self._ticker_cache is None:
            resp = self.http.get("https://www.sec.gov/files/company_tickers.json")
            resp.raise_for_status()
            data = resp.json()
            # data is dict with numeric keys, each value has ticker, cik_str, title
            by_ticker = {v["ticker"].upper(): v for v in data.values()}
            self._ticker_cache = by_ticker
        if self._ticker_exchange_cache is None:
            try:
                resp2 = self.http.get("https://www.sec.gov/files/company_tickers_exchange.json")
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    by_ticker2 = {v["ticker"].upper(): v for v in data2.values()}
                    self._ticker_exchange_cache = by_ticker2
                else:
                    self._ticker_exchange_cache = {}
            except Exception:
                self._ticker_exchange_cache = {}

    def resolve_company(self, ticker: str) -> Optional[Dict]:
        self._load_tickers()
        info = (self._ticker_cache or {}).get(ticker.upper())
        return info

    def get_primary_market(self, ticker: str) -> Optional[str]:
        self._load_tickers()
        ex = (self._ticker_exchange_cache or {}).get(ticker.upper())
        if ex and ex.get("exchange"):
            return ex["exchange"]
        return None

    def fetch_recent_filings(self, cik_no_zeros: str) -> Dict:
        # CIK must be zero-padded to 10 for submissions endpoint
        cik_padded = cik_no_zeros.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        resp = self.http.get(url)
        resp.raise_for_status()
        return resp.json()

    def list_filings_last_n_years(self, ticker: str, n_years: int) -> List[SecFiling]:
        info = self.resolve_company(ticker)
        if not info:
            return []
        cik_str = str(info.get("cik_str"))
        submissions = self.fetch_recent_filings(cik_str)
        company_name = submissions.get("name") or info.get("title", "")
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])
        accession_numbers = recent.get("accessionNumber", [])

        # cutoff
        cutoff = datetime.utcnow() - timedelta(days=365 * n_years)

        results: List[SecFiling] = []
        for form, fdate, rdate, pdoc, acc_no in zip(forms, filing_dates, report_dates, primary_docs, accession_numbers):
            # Only keep forms we classify
            if not classify_from_sec_form(form):
                continue
            try:
                dt = datetime.strptime(fdate, "%Y-%m-%d")
            except Exception:
                continue
            if dt < cutoff:
                continue
            # Build URL per SEC pattern
            # https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_no_dashes}/{primary_doc}
            acc_no_digits = acc_no.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik_str):d}/{acc_no_digits}/{pdoc}"
            results.append(SecFiling(
                form=form,
                filing_date=fdate,
                report_date=rdate or None,
                primary_doc=pdoc,
                accession_no=acc_no,
                cik=str(int(cik_str)),
                company_name=company_name,
                url=url,
            ))
        return results