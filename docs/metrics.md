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

## Embeddings

| Metric | Value | How measured |
|---|---|---|
| Embedding model | BAAI/bge-small-en-v1.5 (384 dimensions, 512-token limit, runs locally on CPU, no per-call cost) | `src/embed_demo.py` |
| Tokens per chunk | avg 266, 95th percentile 469, max 658 | `src/check_token_lengths.py` |
| Chunks over 256 tokens | 1,689 of 3,408 (49.6%), which a 256-token model would silently truncate | `src/check_token_lengths.py` |
| Chunks over 512 tokens | 81 of 3,408 (2.4%), truncated in the embedding only (full text still sent to the LLM) | `src/check_token_lengths.py` |

| Index build time | 3,408 chunks embedded and stored in 289 seconds (about 12 chunks/s) on a laptop CPU | `src/build_index.py` |

## Retrieval baseline (v1: bge-small-en-v1.5, 1,500-char chunks, top-5)

| Metric | Result | Source |
|---|---|---|
| Eval set | 16 questions (12 answerable, 4 unanswerable); retrieval scored on the 12 answerable (16 gold items) | evals/questions.jsonl |
| Recall@1 | 6/16 = 38% | src/eval_retrieval.py |
| Recall@3 | 10/16 = 62% | src/eval_retrieval.py |
| Recall@5 | 10/16 = 62% | src/eval_retrieval.py |
| Recall@10 | 10/16 = 62% (nothing found at ranks 6-10, so raising k alone does not help) | src/eval_retrieval.py |
| MRR | 0.479 | src/eval_retrieval.py |
| Full-hit@5 by question type | recent_fact 1/1, single_fact 3/3, exact_number 3/4, cross_company 0/4 | src/eval_retrieval.py |
| Scoring note | First run with strict single-source matching gave Recall@5 44% and MRR 0.374. After accepting the same fact from a second document (press release or 10-Q), Recall@5 is 62% and MRR 0.479. This is a correction of false misses in the eval, not a system improvement, so the baseline is 62% / 0.479. | evals/validate_questions.py |
| Failure patterns found | Cross-company questions retrieve only one of the two companies. Bare table rows rank poorly (AMD net income not in the top 50 of 3,408 chunks). | src/debug_retrieval.py |
| Caveat | Small eval set; expand to about 40 questions before quoting numbers externally | |