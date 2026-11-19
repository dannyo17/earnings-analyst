import os
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.environ["SEC_USER_AGENT"]}

TICKERS = ["NVDA", "AMD", "MSFT", "AMZN"]
CUTOFF = "2026-11-19"  # only filings on or before this date
QUARTERS = 4  # most recent reported quarters per company


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
        recent["primaryDocument"],
    )
    filings = []
    for form, filed, period, accession, items, primary_doc in rows:
        is_report = form in ("10-K", "10-Q")
        is_release = form == "8-K" and "2.02" in items
        if is_report or is_release:
            filings.append(
                {
                    "form": form,
                    "filed": filed,
                    "period": period,
                    "accession": accession,
                    "primary_doc": primary_doc,
                }
            )
    return data["name"], filings


def filing_folder(cik, accession):
    """URL of the folder that holds all files of one filing."""
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}"


def build_manifest(cik):
    """Pair each of the latest earnings releases with its 10-K/10-Q."""
    name, filings = get_filings(cik)
    filings = [f for f in filings if f["filed"] <= CUTOFF]
    releases = [f for f in filings if f["form"] == "8-K"][:QUARTERS]
    reports = [f for f in filings if f["form"] in ("10-K", "10-Q")]

    manifest = []
    for release in releases:
        filed = date.fromisoformat(release["filed"])
        window_end = filed + timedelta(days=7)
        report = next(
            (
                r for r in reports
                if filed <= date.fromisoformat(r["filed"]) <= window_end
            ),
            None,
        )
        manifest.append({"release": release, "report": report})
    return name, manifest


if __name__ == "__main__":
    cik_map = get_cik_map()
    for ticker in TICKERS:
        cik = cik_map[ticker]
        name, manifest = build_manifest(cik)
        print(f"\n{name} ({ticker})")
        for item in manifest:
            release, report = item["release"], item["report"]
            if report:
                url = f"{filing_folder(cik, report['accession'])}/{report['primary_doc']}"
                print(
                    f"  release {release['filed']} | {report['form']} filed "
                    f"{report['filed']} (period {report['period']})"
                )
                print(f"    {url}")
            else:
                print(f"  release {release['filed']} | no 10-K/10-Q filed yet")