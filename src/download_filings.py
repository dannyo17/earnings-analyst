import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sec_explore import HEADERS, TICKERS, build_manifest, filing_folder, get_cik_map

RAW = Path("data/raw")


def download(url, path):
    """Download one file, skipping it if we already have it."""
    if path.exists():
        print(f"skip (already have): {path}")
        return
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print(f"saved: {path} ({len(response.content):,} bytes)")
    time.sleep(0.2)  # stay well under SEC's limit of 10 requests per second


def find_exhibits(cik, accession):
    """Read a filing's index page and return its EX-99.x HTML exhibits."""
    index_url = f"{filing_folder(cik, accession)}/{accession}-index.htm"
    response = requests.get(index_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    time.sleep(0.2)
    soup = BeautifulSoup(response.text, "lxml")

    exhibits = []
    for row in soup.select("table.tableFile tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        doc_type = cells[3].get_text(strip=True)
        link = cells[2].find("a")
        if (
            doc_type.startswith("EX-99")
            and link
            and link["href"].lower().endswith((".htm", ".html"))
        ):
            exhibits.append((doc_type, "https://www.sec.gov" + link["href"]))
    return exhibits


if __name__ == "__main__":
    cik_map = get_cik_map()
    for ticker in TICKERS:
        cik = cik_map[ticker]
        _, manifest = build_manifest(cik)
        for item in manifest:
            report, release = item["report"], item["release"]

            # 10-K / 10-Q
            if report is not None:
                folder = filing_folder(cik, report["accession"])
                url = f"{folder}/{report['primary_doc']}"
                name = f"{ticker}_{report['form']}_{report['period']}.htm"
                download(url, RAW / ticker / name)

            # Earnings release exhibits (press release, CFO commentary, ...)
            for doc_type, url in find_exhibits(cik, release["accession"]):
                name = f"{ticker}_8-K_{doc_type}_{release['filed']}.htm"
                download(url, RAW / ticker / name)