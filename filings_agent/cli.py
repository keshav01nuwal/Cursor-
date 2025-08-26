import argparse
from typing import Optional

from .orchestrator import run_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filings-agent",
        description="Retrieve investor documents from IR sites and regulators for the last 3 years",
    )
    parser.add_argument("--ticker", required=True, help="Company ticker symbol (e.g., AAPL, MSFT)")
    parser.add_argument("--company-name", help="Optional company name for disambiguation")
    parser.add_argument("--country", help="Optional country (e.g., US, CA, GB, AU, EU)")
    parser.add_argument("--market", help="Optional primary market/exchange (e.g., NASDAQ, NYSE, LSE, ASX)")
    parser.add_argument("--max-years", type=int, default=3, help="Number of past years to collect (default: 3)")
    parser.add_argument(
        "--out-root",
        default="/",
        help="Output root directory (default: /). Company directory will be created under this root.",
    )
    parser.add_argument(
        "--ir-only",
        action="store_true",
        help="Only use IR site, skip regulator sources (not recommended)",
    )
    parser.add_argument(
        "--reg-only",
        action="store_true",
        help="Only use regulator/exchange sources, skip IR site",
    )
    parser.add_argument(
        "--user-agent",
        default="filings-agent/0.1 (+https://example.org; contact admin@example.org)",
        help="HTTP User-Agent string for regulator requests (SEC requires descriptive UA)",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=4,
        help="Max concurrent HTTP requests per host (default: 4)",
    )
    parser.add_argument(
        "--log-file",
        default="run.log",
        help="Log file name to write progress logs (default: run.log)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_agent(
        company_ticker=args.ticker,
        company_name=args.company_name,
        country=args.country,
        market=args.market,
        max_years=args.max_years,
        out_root=args.out_root,
        ir_only=args.ir_only,
        reg_only=args.reg_only,
        user_agent=args.user_agent,
        max_concurrency=args.max_concurrency,
        log_file=args.log_file,
    )
    return 0