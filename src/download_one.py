import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"User-Agent": os.environ["SEC_USER_AGENT"]}

url = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm"
out = Path("data/raw/nvda_10q_2026-07-26.htm")
out.parent.mkdir(parents=True, exist_ok=True)

response = requests.get(url, headers=HEADERS, timeout=60)
response.raise_for_status()
out.write_bytes(response.content)

print(f"Saved {out} ({len(response.content):,} bytes)")