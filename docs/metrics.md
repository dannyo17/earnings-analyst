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

## End-to-end answer quality (16 questions; Haiku generates, Sonnet grades; top-5 passages)

| Metric | RAG, company-aware retrieval | RAG, original retrieval | Same model, no documents |
|---|---|---|---|
| Answerable questions correct | 11/12 (92%) | 11/12 (92%) | 0/12 |
| Confidently wrong on answerable questions | 0 | 0 | 1 in one run, 0 in another |
| Refused on answerable questions | 1 (q016) | 1 (q016) | 11 to 12 |
| Unanswerable questions correctly refused | 4/4 | 4/4 | 3/4 (invented an Intel revenue figure in both runs) |
| Citation accuracy (correct answers citing a passage with the gold evidence) | 9/11 | 9/11 | n/a |
| Answered correctly when retrieval reached the evidence | 9/9 | 9/9 | n/a |
| Average time per question | 1.82 s | 1.85 s | not timed |
| Average tokens per question | 3,057 in, 300 out | 3,059 in, 312 out | not measured |
| Caveat: rounding | 2 of the 11 correct answers (q006, q008) used the press-release precision ($2.4 billion, $201.9 billion); the grader accepted them against exact table figures | same | |
| Caveat: baseline varies | No-retrieval answers differ between runs, so that column is approximate | | |
| Caveat: size | Small, easy set; expand to about 40 harder questions before quoting externally | | |
| Finding | Company-aware retrieval improved MRR (0.523 to 0.542) but did not change any final answer | | |
| Raw outputs | evals/results/answers_routed.json, evals/results/answers_baseline.json | | |

## Eval set v2 (22 questions: 17 answerable with 22 gold evidence items, 5 unanswerable)

Earlier tables used the 16-question set and are not comparable with these numbers.

| Retrieval metric | Original search | Company-aware |
|---|---|---|
| Recall@1 | 9/22 = 41% | 9/22 = 41% |
| Recall@3 | 14/22 = 64% | 15/22 = 68% |
| Recall@5 | 16/22 = 73% | 16/22 = 73% |
| Recall@10 | 16/22 = 73% | 16/22 = 73% |
| MRR | 0.526 | 0.539 |
| Full-hit@5 by type | recent 1/1, single 4/4, exact 5/7, cross 2/4, multi 0/1 | same |
| Average search time | 0.02 s | 0.02 s |

| End-to-end metric (company-aware retrieval, top 5) | RAG | Same model, no documents |
|---|---|---|
| Answerable questions correct | 16/17 (94%) | 0/17 |
| Confidently wrong | 0 | 1 (Azure growth) |
| Refused on answerable questions | 1 (q016) | 16 |
| Unanswerable questions correctly refused | 5/5 | 4/5 (invented an Intel figure) |
| Citation accuracy | 12/16 | n/a |
| Answered correctly when retrieval reached the evidence | 12/12 | n/a |
| Average time / tokens per question | 1.83 s; 3,138 in, 314 out | n/a |
| Caveat | q020 (10-K "Total" row) and q021 (AMD outlook) were answered correctly although the strict check found no gold chunk, because the same facts appear in other passages. The set is nearly saturated at 16/17, so it cannot show further improvement. | |

## Eval set v3 (28 questions: 22 answerable, 6 unanswerable)

Question mix: recent_fact 1, single_fact 7, exact_number 7, cross_company 5, multi_section 2, unanswerable 6.
v3 is a different and harder set than v1 (16) and v2 (22), so its numbers are **not comparable** with theirs.
Corpus and system are the same as v2 (bge-small embeddings, Chroma, routed retrieval, k=5, Claude Haiku answers, Claude Sonnet judge). The system did not change between any of the three measurements below; only the measurement did.

### How the v3 measurement was corrected (system unchanged)

| Step | What changed | Retrieval Recall@5 (baseline / routed) | MRR (baseline / routed) | Full-hit@5 | End-to-end correct |
|---|---|---|---|---|---|
| 1. First run | Nothing (6 new questions added, single-source labels, lenient judge) | 62% (18/29) / 62% (18/29) | 0.423 / 0.433 | 13/22 | 19/22 |
| 2. Label correction | 9 alternate evidence strings added on 4 questions (q013, q020, q024, q027). Each is verified verbatim in the processed files and was the passage the model actually answered from | 76% (22/29) / 76% (22/29) | 0.518 / 0.520 | 17/22 | not re-run |
| 3. Stricter judge | Judge now requires the exact figure (no rounding to fewer digits), all facts in a multi-part reference, and no "part is unavailable" answers | unchanged | unchanged | 17/22 | **15/22 (68%)** |

These are **measurement corrections, not improvements**. Steps 2 and 3 are the eval catching up with what the system was already doing: the labels missed chunks that really contain the fact, and the lenient judge accepted rounded and partial answers. If rounding is tolerated, the end-to-end score is 19/22.

### v3 end-to-end results (routed, k=5, strict judge)

| Metric | RAG | No retrieval |
|---|---|---|
| Answerable correct (22) | **15/22 (68%)** | 0/22 |
| Answerable incorrect | 5 | 1 |
| Answerable refused | 2 | 21 |
| Unanswerable correctly refused (6) | **6/6** | 4/6 (invented answers on q010, q028) |
| Citations containing gold evidence | 15/15 of correct answers | n/a |
| Retrieval reached all gold in top 5 | 17/22; of those, answered correctly 15/17 | n/a |
| Average time per question | 1.89 s | |
| Average tokens per question | 3,136 in / 316 out | |

### Why the 7 non-correct answers failed (0 fabricated figures)

| Category | Questions | What happened |
|---|---|---|
| Rounded away the exact figure | q006, q008, q015 | Facts correct, precision lost: $2.4B vs $2,428M, $201.9B vs $201,944M, $92.3B vs $92.279B. For q008 and q015 the exact figure was in the retrieved chunks, but the model used the rounded narrative figure |
| Retrieval miss, partial answer | q021, q026 | Q4 outlook sentence and June-quarter Azure growth never surfaced; the model reported what it found and said the rest was not in the passages |
| Retrieval miss, refusal | q016, q025 | Amazon net income and the 10-K employee count were not retrieved; the system said "I don't know" |

Known grader note: q015 asks which company is higher and the answer correctly says NVIDIA; the strict judge failed it only because Microsoft's $92.279B was rounded to $92.3B. It is counted as incorrect and left that way, because the judge is not changed after seeing results.

### Retrieval misses that remain (real, not labeling)

q006 (AMD net income table row), q016 (AMD and Amazon net income), q021 (Q4 outlook sentence), q025 (10-K employee count), q026 (Azure growth, both quarters). Recall@5 equals Recall@10, so these chunks are not in the top 10 at all.
Routing adds almost nothing on this set (MRR 0.520 vs 0.518; Recall@3 and Recall@5 identical).

## Next experiments (one change at a time, before/after row for each, kept only if it helps)

1. Generation prompt: prefer the exact table figure over a rounded narrative figure. Targets q008 and q015 (exact figure already retrieved). Does not help q006, whose exact row is not retrieved.
2. Table-aware chunking or row labels, so bare rows like "Net income | 2,428 | ..." carry their company, period and metric. Targets q006, q016.
3. Hybrid retrieval (BM25 + vector) for numeric and exact-phrase queries. Targets q025 and other 10-K prose.
4. Cross-company and cross-quarter query splitting. Targets q016, q026.
5. Chunk size and overlap.
6. Larger reranker (the small one did not help in experiment 3).
7. Before tuning further, add held-out questions that no experiment was tuned on, to guard against overfitting to these 28.