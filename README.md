# Filings Agent

Autonomous Python agent that, given a company ticker (and optional company name/country/market), resolves the correct listed company, selects a primary market, and retrieves official investor documents for the last 3 years from the company's IR site and primary regulator/exchange.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_agent.py --help
```

## Usage

```bash
python run_agent.py \
  --ticker AAPL \
  --company-name "Apple Inc." \
  --country US \
  --market NASDAQ \
  --max-years 3 \
  --out-root / \
  --user-agent "your-app/1.0 (your-email@example.com)"
```

The agent will save documents under `/{Company}/{YYYY}/{DocType}/` and emit `metadata.csv`, `metadata.json`, and `run.log` in the company root.

### Example: SEC-only for Microsoft

```bash
python run_agent.py --ticker MSFT --reg-only --out-root /workspace/output \
  --user-agent "filings-agent/0.1 (admin@example.org)"
```
