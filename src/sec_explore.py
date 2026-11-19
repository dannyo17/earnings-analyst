import os
import requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.environ["SEC_USER_AGENT"]}

TICKERS = ["NVDA", "AMD", "MSFT", "AMZN"]


def get_cik_map():
    """Map each ticker to its 10-digit CIK, using SEC's lookup file."""
    url = "https://www.sec.gov/files/company_tickers.json"
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    return {e["ticker"]: str(e["cik_str"]).zfill(10) for e in data.values()}


def get_filings(cik):
    """Return the company name and its 10-K, 10-Q and earnings 8-K filings."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    recent = data["filings"]["recent"]
    rows = zip(
        recent["form"],
        recent["filingDate"],
        recent["reportDate"],
        recent["accessionNumber"],
        recent["items"],
    )
    wanted = [
        r for r in rows
        if r[0] in ("10-K", "10-Q") or (r[0] == "8-K" and "2.02" in r[4])
    ]
    return data["name"], wanted


if __name__ == "__main__":
    cik_map = get_cik_map()
    for ticker in TICKERS:
        name, filings = get_filings(cik_map[ticker])
        print(f"\n{name} ({ticker})")
        for form, filed, period, accession, items in filings[:8]:
            print(form, filed, period, accession, items)