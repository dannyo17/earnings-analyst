# Project metrics log

Every number here comes from a real run, with the script that produced it. Add a row each time we measure something. Resume bullets and interview answers use only numbers from this file.

## Corpus (cutoff date 2026-11-19)

| Metric | Value | How measured |
|---|---|---|
| Companies | 4 (NVDA, AMD, MSFT, AMZN) | corpus rule |
| Quarters per company | 4 most recent reported | `src/sec_explore.py` manifest |
| Documents downloaded | 44 (15 10-K/10-Q + 29 earnings-release exhibits) | `src/download_filings.py` |
| Documents indexed | 40 (4 boilerplate exhibits under 5,000 chars skipped) | `src/build_chunks.py` |
| Indexed text | 4,190,907 characters in 3,408 chunks | `src/build_chunks.py` |

## Data cleaning and chunking

| Change | Before | After | Change % | How measured |
|---|---|---|---|---|
| Strip hidden XBRL header (Nvidia Q2 FY27 10-Q) | 174,563 chars | 148,059 chars | -15.2% | `src/inspect_filing.py` |
| Chunks under 200 chars (page numbers, stray headings) | 47 | 2 | -95.7% | `src/inspect_chunks.py` |
| Chunks over 2,500 chars (whole slide decks on one line) | 76 | 0 | -100% | `src/inspect_chunks.py` |
| Largest chunk | 8,269 chars | 1,670 chars | -79.8% | `src/build_chunks.py` |

Fix: split oversized lines at sentence boundaries, fold tiny chunks into the previous chunk.