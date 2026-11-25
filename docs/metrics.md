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
System throughout: bge-small embeddings, Chroma, routed retrieval, k=5, Claude Haiku answers, Claude Sonnet judge. The system did not change between the four measurement steps below; only the measurement did.

### How the v3 measurement was corrected (system unchanged)

| Step | What changed | Recall@5 (baseline / routed) | MRR (baseline / routed) | Full-hit@5 | End-to-end correct |
|---|---|---|---|---|---|
| 1. First run | 6 new questions, single-source labels, lenient judge | 62% (18/29) / 62% | 0.423 / 0.433 | 13/22 | 19/22 |
| 2. Label correction A | 9 alternate evidence strings added on 4 questions (q013, q020, q024, q027). Each verified verbatim in the processed files and was the passage the model actually answered from | 76% (22/29) / 76% | 0.518 / 0.520 | 17/22 | not re-run |
| 3. Stricter judge | Judge requires the exact figure (no rounding to fewer digits), every fact in a multi-part reference, and no "part is unavailable" answers | unchanged | unchanged | 17/22 | 15/22 |
| 4. Label correction B | 2 alternates removed (q008, q015) because they stated the figure less precisely than the reference answer, so retrieving them could not produce a passing answer | **69% (20/29) / 69%** | **0.466 / 0.468** | **15/22** | **15/22** (re-run) |

Rule adopted in step 4: an alternate counts as retrieval success only if the chunk states the fact at least as precisely as the reference answer, because the judge enforces that precision.
All four steps are **measurement corrections, not improvements**; the system was never changed. Steps 2 and 4 moved retrieval in opposite directions. If rounding is tolerated, the end-to-end score is 19/22.

### v3 baseline (final labels, strict judge)

| Metric | Result |
|---|---|
| Retrieval Recall@1 / @3 / @5 / @10 | 34% / 55% / 69% (20/29) / 69% |
| Retrieval MRR (baseline / routed) | 0.466 / 0.468 |
| Full-hit@5 by type | recent_fact 1/1, single_fact 6/7, exact_number 5/7, cross_company 3/5, multi_section 0/2 |
| Answerable correct (22) | **15/22 (68%)**, 6 incorrect, 1 refused |
| No retrieval, same model | 0/22 correct (21 refused, 1 incorrect) |
| Unanswerable correctly refused (6) | **RAG 6/6**, no retrieval 4/6 (invented answers on q010 and q028) |
| Citations containing gold evidence | 15/15 of correct answers |
| Retrieval reached all gold in top 5 | 15/22; **answered correctly 15/15** |
| Average time per question | 1.79 s |
| Average tokens per question | 3,136 in / 313 out |

The same 15 questions were correct in all three strict-judge runs. The only verdict that varied was q016 (refused in two runs, incorrect in one, because the answer opened with "I don't know" and then listed partial facts); the retrieval miss behind it is identical in all three.

### Why the 7 non-correct answers failed (every one is a retrieval failure; no answer stated a wrong figure)

| Category | Questions | What happened |
|---|---|---|
| Exact table row not retrieved (not in the baseline top 50) | q006, q008, q015 | AMD net income row, Amazon "Total net sales | 180,169 | 201,944" row (10-Q chunk 005) and Microsoft "Total revenue | 92,279" row (chunk 010) never surfaced. The model had only the rounded narrative figure ($2.4B, $201.9B, $92.3B), used it, and said no full-precision figure was available |
| Chunk not retrieved, partial answer | q021, q026 | Q4 outlook sentence and June-quarter Azure growth never surfaced; the model reported what it found and said the rest was not in the passages |
| Chunk not retrieved, refusal | q016, q025 | Amazon net income and the 10-K employee count were not retrieved; the system said "I don't know" |

Known grader note: q015 asks which company is higher, and the answer correctly says NVIDIA. It fails only because Microsoft's $92.279B was rounded to $92.3B. It is counted as incorrect; the judge is not changed after seeing results.
Routing adds almost nothing on this set (MRR 0.468 vs 0.466; Recall@3 and Recall@5 identical).

### Experiment 1 (v3): generation prompt, prefer full-precision figures

Hypothesis: the model had the exact figure and used the rounded narrative one. Added to the system prompt: when a figure appears both rounded and in full precision, give the full-precision one.
Result: **no effect.** Answerable correct 15/22 before and after, the same questions failed, 6/6 refusals unchanged. Tokens went from 3,136 in / 316 out to 3,211 in / 346 out; time from 1.89 s to 1.93 s; answers gained hedging sentences. **Reverted.**
Why it could not work: the exact table rows were not being retrieved, so there was no full-precision figure in the context to prefer (see the failure table). This was diagnosed afterwards; the hypothesis was wrong.
Saved: evals/results/answers_routed_exp1_exact_figures_prompt.json.

## Next experiments (one change at a time, before/after row for each, kept only if it helps)

1. **Table-aware chunking or row labels**, so bare rows like "Total net sales | 180,169 | 201,944 | ..." carry their company, period and metric and can be retrieved at all. Targets q006, q008, q015, q016.
2. Hybrid retrieval (BM25 + vector) for exact numbers and phrases. Targets q025 and other 10-K prose, possibly q021.
3. Cross-company and cross-quarter query splitting. Targets q016, q026.
4. Chunk size and overlap.
5. Larger reranker (the small one did not help in an earlier experiment).
6. Before tuning further, add held-out questions that no experiment was tuned on, to guard against overfitting to these 28.

## Retrieval experiments on v3 (baseline: routed, 1,500-char chunks, bge-small, k=5)

One change at a time, kept only if it helps. Baseline routed: Recall@5 69% (20/29), Recall@10 69%, MRR 0.468, full-hit@5 15/22.

| # | Change | Recall@5 | Recall@10 | MRR | Full-hit@5 | Verdict |
|---|---|---|---|---|---|---|
| 2 | Hybrid retrieval: BM25 + vector, reciprocal rank fusion (vs baseline 69%, 0.466, 15/22) | 52% (15/29) | 55% | 0.410 | 10/22 | Worse; not adopted |
| 3 | Chunk size 1,500 to 600 chars (8,583 chunks); baseline / routed | 31% / 38% | 45% / 52% | 0.200 / 0.202 | 5/22 / 6/22 | Much worse; reverted and verified |
| 4 | Period-aware routing: keep only documents dated within 60 days after a date named in the question | 69% (20/29) | 76% (22/29) | 0.507 | 15/22 | Missed the pre-set criterion (full-hit@5 above 15/22); ranking gains only; not adopted as default |

What the diagnostics showed:
- The failing gold chunks rank 52 to 113 in vector search (q006 112, q008 113, q015 52; q025 beyond 200) and 31 to 509 in BM25 (q006 31, q008 76, q015 129, q025 509). Neither method puts them in the top 10.
- BM25 ranked chunks that vector search had at rank 1 much lower (q005 at 106, q017 at 19). Our questions share words that appear in nearly every financial table (three months ended, revenue, net income, dates), so word matching adds noise. This is why hybrid lost.
- Smaller chunks helped single-sentence answers (q021 outlook sentence: not found to rank 4; q023: rank 5 to 2) but collapsed table-row questions (exact_number full-hit@5 from 5/7 to 0/7 baseline and 1/7 routed), because a 600-character slice of a table usually lacks the period header and company name.
- Restricting search to the right company and period (a handful of documents) still left q006, q008, q015 (Microsoft item) and q025 outside the top 10. The remaining failures are within-document ranking by the embedding model, not near-duplicate quarters alone.
- Experiments 2 to 4, plus the earlier reranker, are four attempts with no adopted gain. By the pre-agreed rule (stop after three in a row), retrieval tweaks on this pipeline stop here.

Known limitation of period-aware routing: it only helps when the question states an explicit date, and all of our test questions do, so any benefit would be overstated for real users who say "last quarter".
Code for experiments 2 to 4 stays in src/search.py as unused modes (hybrid, dated) and src/eval_retrieval.py (hybrid, dated); the default remains routed.

### Experiment 5: embedding model bge-small-en-v1.5 to bge-base-en-v1.5 (same chunks, same query prefix)

| Mode | Recall@5 | Recall@10 | MRR | Full-hit@5 | Search time |
|---|---|---|---|---|---|
| bge-small baseline / routed | 69% (20/29) / 69% | 69% / 69% | 0.466 / 0.468 | 15/22 / 15/22 | 0.02 s / 0.03 s |
| bge-base baseline / routed | 48% (14/29) / 52% (15/29) | 62% / 66% | 0.372 / 0.368 | 10/22 / 11/22 | 0.05 s / 0.06 s |

Verdict: **worse, reverted** (index restored from backup and verified at 69% / 0.468 / 15/22). Index build time 866 s vs about 300 s for bge-small. It fixed q020 and q001 but lost q021, q014, q018 and q027. A larger model did not help on numeric tables and near-identical filings.

## Retrieval phase conclusion

Adopted: company routing (detect NVDA, AMD, MSFT, AMZN in the question and search only their chunks). Everything else tested and rejected: chunk context header, cross-encoder reranker, hybrid BM25 + vector, 600-character chunks, period-aware filtering, bge-base embeddings, and an exact-figure generation prompt.
Final system: bge-small-en-v1.5, 1,500-character chunks, routed retrieval, k=5, Claude Haiku answers.
Final v3 result (strict judge, corrected labels): 15/22 answerable correct (68%), 6/6 unanswerable refused, 0/22 for the same model with no retrieval, and 15/15 correct whenever the evidence reached the top 5.
Known limitations, from the failing questions: exact table rows in 10-Q/10-K statements (q006, q008, q015, q016), 10-K prose such as the employee count (q025), outlook sentences next to similar quarters (q021), and cross-quarter comparisons (q026). The failure mode is almost always a refusal or a rounded figure, not an invented one. Company routing and the date-explicit questions mean results are likely better than for real users who phrase questions vaguely.


## Retrieval experiments 6-8 and failure diagnosis (2026-11-24 and 2026-11-25)

All numbers use the frozen v3 question set and the same scoring as `eval_retrieval.py`. Baseline for comparison: routed retrieval, Recall@5 69%, MRR 0.468, full-hit@5 15/22.

### Diagnosis of the 7 failing questions

Ranks of each gold evidence item under routed retrieval (searching 150 deep) were 99, 85, 36, over 150, 34, 116, over 150 and 11 to 35. In every case, the document that holds the evidence appeared among the sources of the top 3 retrieved chunks. The failure is locating the right chunk inside the right document, not finding the document.

Causes found in the failing chunks:
- Table rows are bare numbers (`Net income | 2,428 | 1,243 | ...`) with no company or period; the column headers are several lines above.
- Dilution: one relevant sentence sits inside a 1,500-character chunk about other topics.
- Near-duplicate filings from adjacent quarters compete.
- A date in the question (for example "January 25, 2026") matches the column headers of financial-table chunks and outranks the right chunk (q025).

What the app answered on the 7 failures:
- q006, q008, q015: the correct figure, rounded the way the press release rounds it ($2.4 billion, $201.9 billion, $92.3 billion). The strict judge requires the exact table figure, so they are graded incorrect.
- q021, q026: answered one part and said it could not find the other part. No number was invented.
- q016, q025: said "I don't know" or could not complete the comparison.

Reporting: strict exact-figure accuracy is 15/22 (68%). Counting the three rounded answers as correct would give 18/22 (82%). That second figure is post hoc: I read those three answers by hand after seeing the results, so it is reported only alongside the strict number, never alone.

### Experiment 6: doc-first retrieval (not adopted)

Pick the top 2 or 3 documents per company from the vector search, then rank only the chunks inside those documents with vector similarity fused with BM25.

| Setting | Recall@5 | MRR | Full-hit@5 | Questions lost |
|---|---|---|---|---|
| Routed (baseline) | 69% | 0.468 | 15/22 | |
| 2 docs, 3 chunks each | 59% | 0.444 | 12/22 | q019, q020, q023 |
| 3 docs, 2 chunks each | 55% | 0.434 | 11/22 | q005, q019, q020, q023 |

No question was gained. An earlier run of this experiment ignored `also_accept` alternates and showed two false gains; fixing the script to use the official `first_rank` reproduced the baseline exactly (69%, 0.468, 15/22).

### Experiment 7: contextual retrieval (not adopted)

For each of the 3,408 chunks, Claude Haiku 5.5 wrote 1 to 3 sentences placing the chunk in its document (company, document type, period, statement, what each column means). The context was prepended to the chunk for embedding only; the stored text stayed the original. Generation: 0 failures, 5.04M input and 0.55M output tokens, about $0.78. The 5 sample contexts checked by hand contained no invented facts.

| Index | Recall@5 | MRR | Full-hit@5 | Questions lost |
|---|---|---|---|---|
| Plain (baseline) | 69% | 0.468 | 15/22 | |
| Contextual | 59% | 0.281 | 11/22 | q005, q014, q017, q023 |

Some hard items improved (q021's outlook sentence from rank 116 to 3; q015's Microsoft revenue row from 36 to 10), but the easy questions regressed. Chunks over the model's 512-token limit rose from 81 (2.4%) to 297 (8.7%) once context was added. My hypothesis, not tested: the shared context language makes chunks from the same filing look alike.

### Experiment 8: fusing the plain and contextual indexes (not adopted)

Search both indexes per company, 30 candidates each, combine with reciprocal rank fusion (k=60).

| | Recall@5 | MRR | Full-hit@5 | Questions lost |
|---|---|---|---|---|
| Fused | 62% | 0.390 | 12/22 | q013, q014, q023 |

### Conclusion

Eight ranking and indexing changes were tested against the same frozen set (experiments 2 to 8, plus company routing). Only routing was adopted. By the exit rule agreed beforehand, retrieval experiments stop. The remaining misses are a documented limitation, not an unexplained failure.


## Held-out evaluation (2026-11-25)

### Method
- 40 passages were sampled with a fixed seed (2026), 10 per company, by `src/sample_passages.py`.
- The first 33 passages were used: 20 produced an answerable question and 13 were skipped because they held no specific fact (boilerplate, exhibit lists, legal language). No passage was skipped for retrieval difficulty.
- 20 answerable and 3 unanswerable questions: `evals/heldout.jsonl`.
- Alternate evidence (`also_accept`) was decided before the first run, using `src/find_figures.py` and `src/find_phrase.py` and the same precision rule as the original set. 17 alternates on 6 questions.
- The set was committed to git before the first run and run once on the final system (plain index, routed retrieval, k=5, same judge). No labels were changed afterward.

### Results (held-out, 20 answerable + 3 unanswerable)

| | RAG | No retrieval |
|---|---|---|
| Answerable correct | 12/20 (60%) | 1/20 |
| Unanswerable correctly refused | 3/3 | 2/3 |
| Correct when evidence reached the top 5 | 10/10 | |

Retrieval: Recall@5 10/20 (50%), Recall@10 55%, MRR 0.377. Full-hit@5: single_fact 9/15, exact_number 1/5.

### Original 28 vs held-out 23 vs combined 51

| | Original (studied) | Held-out (unseen) | Combined |
|---|---|---|---|
| Answerable correct (RAG) | 15/22 (68%) | 12/20 (60%) | 27/42 (64%) |
| Answerable correct (no retrieval) | 0/22 | 1/20 | 1/42 (2%) |
| Unanswerable correctly refused (RAG) | 6/6 | 3/3 | 9/9 |
| Unanswerable correctly refused (no retrieval) | 4/6 | 2/3 | 6/9 |
| Correct when evidence reached top 5 | 15/15 | 10/10 | 25/25 |
| Recall@5 | 69% | 50% | 61% |

The original set was used to choose routing and to correct labels, so its score is expected to be optimistic. The held-out 60% is the better estimate for new questions, with a wide margin of error (20 questions: roughly plus or minus 20 points).

### What the 8 held-out misses were
- 6 refusals (h004, h005, h011, h012, h014, h018): the evidence was not retrieved. 4 of the 6 were number-heavy table rows or a cover-page figure.
- h006: gave the right figure rounded ($65.3 billion from a summary table; reference $65,287 million). The strict judge rejects it.
- h019: could not isolate the $711 million release from a table and said so, naming why the nearby "873" figure was the wrong number to use.
- No answer contradicted the filings or invented a figure.
- Exact-number questions were again the weak spot: 1 of 5 retrieved.

### Labeling notes (not corrected, by the freeze rule)
- h010: the answer (57%) was correct and cited the right filing, but from a different sentence than the labeled evidence, so retrieval counted it as a miss.
- h015: the app computed 22.6% from two reported figures (reference states 23%). The judge accepted it as a matching calculation; retrieval counted it as a miss because the 23% sentence was not retrieved.
- Counting the rounded h006 answer as correct would give 13/20 on held-out and 31/42 combined (74%). That figure is reported only alongside the strict one, because I judged the answer by hand after seeing the results.

### Limitations
- 20 answerable questions is a small sample.
- Random passages produce mostly single-fact and exact-number questions, so this mix has no cross-company or multi-section questions and is not directly comparable to the original set.