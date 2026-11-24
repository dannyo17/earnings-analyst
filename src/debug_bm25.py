import json
import sys

from search import ROOT, _lexical, retrieve


def options(gold):
    found = [(gold["source"], gold["evidence"])]
    found += [(a["source"], a["evidence"]) for a in gold.get("also_accept", [])]
    return found


def rank_of(hits, gold):
    for i, hit in enumerate(hits, start=1):
        for source, evidence in options(gold):
            if hit["source"] == source and evidence in hit["text"]:
                return i
    return None


with open(ROOT / "evals" / "questions.jsonl", encoding="utf-8") as f:
    questions = {q["id"]: q for q in (json.loads(line) for line in f if line.strip())}

ids = sys.argv[1:] or ["q005", "q006", "q008", "q015", "q017", "q020", "q023", "q025"]

for qid in ids:
    q = questions[qid]
    vector_hits = retrieve(q["question"], 200)
    lexical_hits = _lexical(q["question"], 5000)
    print(f"\n{qid}: {q['question'][:90]}")
    for g in q["gold"]:
        print(
            f"   gold {g['evidence'][:50]!r}: "
            f"vector rank (of 200) = {rank_of(vector_hits, g)}, "
            f"BM25 rank (of {len(lexical_hits)}) = {rank_of(lexical_hits, g)}"
        )