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
| Recall@3 | 11/16 = 69% | src/eval_retrieval.py |
| Recall@5 | 12/16 = 75% | src/eval_retrieval.py |
| Recall@10 | 12/16 = 75% (nothing found at ranks 6-10, so raising k alone does not help) | src/eval_retrieval.py |
| MRR | 0.523 | src/eval_retrieval.py |
| Full-hit@5 by question type | recent_fact 1/1, single_fact 3/3, exact_number 3/4, cross_company 2/4 | src/eval_retrieval.py |
| Scoring note | The first run used strict single-source matching (Recall@5 44%, MRR 0.374). I then accepted the same fact from a second document (press release or 10-Q) wherever it appeared, which gave 62% / 0.479, and added Microsoft's headline sentence, which gave 75% / 0.523. These were corrections of false misses in the eval, not system improvements, so the baseline is 75% / 0.523. | evals/questions.jsonl |
| Eval freeze | From this point the gold labels only change to fix a demonstrated labeling error, and any such fix is made before the next measurement, so before/after comparisons stay fair. | |
| Remaining failures | AMD net income (q006, q016) and the AMD Data Center figure in q013 are not retrieved; Amazon net income (q016) is not retrieved. | src/debug_retrieval.py |
| Caveat | Small eval set; expand to about 40 questions before quoting numbers externally | |

## Experiments (before / after)

| # | Change | Recall@5 | MRR | Full-hit@5 (recent / single / exact / cross) | Verdict |
|---|---|---|---|---|---|
| 0 | Baseline (bge-small-en-v1.5, 1,500-char chunks) | 75% (12/16) | 0.523 | 1/1, 3/3, 3/4, 2/4 | |
| 1 | Prepend a "company, doc type, date" line to each chunk before embedding (index rebuild 265 s) | 56% (9/16) | 0.383 | 0/1, 3/3, 2/4, 1/4 | Worse, reverted. Fixed the AMD Data Center item in q013, but pushed simple questions down (q001 lost, q002 rank 1 to 3, q004 1 to 4). Recall@10 unchanged at 75%. Hypothesis: shared text on every chunk of a company flattens differences between that company's chunks. |
| 2 | Company-aware retrieval: detect company names in the question, search only those companies' chunks, interleave results when a question names several (no index rebuild) | 75% (12/16) | 0.542 | 1/1, 3/3, 3/4, 2/4 | Small gain: Recall@3 69% to 75%, MRR 0.523 to 0.542, no question lost its top-5 hit. Recall@5 unchanged. AMD net income (q006, q016) and the AMD item in q013 are still not found even when only AMD chunks compete, so the cause is the chunk content (large table blocks), not other companies. |
| 2b | Diagnostic only: routed retrieval measured 50 results deep | Recall@20 81%, Recall@50 88% (14/16) | MRR 0.547 | n/a | Right chunks for AMD Data Center (q013, rank 18) and Amazon net income (q016, rank 34) exist but rank low. AMD net income (q006, and the AMD side of q016) is not in the top 50, so it cannot be fixed by reranking alone. |
| 3 | Rerank 50 company-aware candidates with cross-encoder ms-marco-MiniLM-L-6-v2, keep top 10 | 69% (11/16) | 0.543 | 1/1, 3/3, 3/4, 1/4 | No net gain, not adopted. Recall@1 rose 38% to 44% but Recall@5 fell 75% to 69% and MRR was flat (0.542 to 0.543). Search time went from 0.03 s to 2.31 s per question. Did not rescue the two deep items (q013 AMD at rank 18, q016 Amazon at rank 34). Hypothesis: a reranker trained on web search does not score numeric table chunks well. Current best retrieval: company-aware (experiment 2). |