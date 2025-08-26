import re
from typing import Optional


SEC_FORM_TO_DOCTYPE = {
    "10-K": "10-K",
    "10-Q": "10-Q",
    "20-F": "20-F",
    "6-K": "6-K",
    "40-F": "40-F",
}


TITLE_PATTERNS = [
    (re.compile(r"annual report", re.I), "AnnualReport"),
    (re.compile(r"earnings release|results release|press release", re.I), "EarningsRelease"),
    (re.compile(r"investor presentation|presentation", re.I), "InvestorPresentation"),
    (re.compile(r"data book|supplementary|supplemental", re.I), "SupplementaryDataBook"),
]


def classify_from_sec_form(form: str) -> Optional[str]:
    return SEC_FORM_TO_DOCTYPE.get(form.upper())


def classify_from_title(title: str) -> Optional[str]:
    for pattern, label in TITLE_PATTERNS:
        if pattern.search(title or ""):
            return label
    return None