import json
import sys
import time
from pathlib import Path

from search import retrieve, retrieve_dated, retrieve_hybrid, retrieve_reranked, retrieve_routed

K = 10
KS = (1, 3, 5, 10)
ROOT = Path(__file__).resolve().parent.parent

MODES = {
    "baseline": retrieve,
    "routed": retrieve_routed,
    "reranked": retrieve_reranked,
    "hybrid": retrieve_hybrid,
    "dated": retrieve_dated,
}
MODE = sys.argv[1] if len(sys.argv) > 1 else "baseline"
search_fn = MODES[MODE]


def load_questions():
    questions = []
    with open(ROOT / "evals" / "questions.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def first_rank(hits, gold):
    """1-based rank of the first chunk that contains acceptable evidence for this gold item.
    Acceptable = the main source/evidence, or any 'also_accept' alternative."""
    options = [(gold["source"], gold["evidence"])]
    options += [(a["source"], a["evidence"]) for a in gold.get("also_accept", [])]
    for i, hit in enumerate(hits, start=1):
        for source, evidence in options:
            if hit["source"] == source and evidence in hit["text"]:
                return i
    return None


def main():
    print("Mode:", MODE)
    search_fn("warm up", k=1)  # load models first so timing is fair

    results = []
    seconds = []
    for q in load_questions():
        if not q["gold"]:  # unanswerable: nothing to retrieve
            continue
        start = time.time()
        hits = search_fn(q["question"], k=K)
        seconds.append(time.time() - start)
        ranks = [first_rank(hits, g) for g in q["gold"]]
        results.append((q, ranks))

    print("\nPer question (rank of each gold item, None = not in top", K, ")")
    for q, ranks in results:
        print(f'{q["id"]}  {q["type"]:<14} {ranks}')

    all_ranks = [r for _, ranks in results for r in ranks]
    print(f"\nGold items: {len(all_ranks)} across {len(results)} questions")
    for k in KS:
        found = sum(1 for r in all_ranks if r is not None and r <= k)
        print(f"Recall@{k}: {found}/{len(all_ranks)} = {found / len(all_ranks):.0%}")
    mrr = sum(1 / r for r in all_ranks if r) / len(all_ranks)
    print(f"MRR: {mrr:.3f}")
    print(f"Average search time: {sum(seconds) / len(seconds):.2f} s per question")

    print("\nFull-hit@5 by question type (all gold items in top 5)")
    by_type = {}
    for q, ranks in results:
        ok = all(r is not None and r <= 5 for r in ranks)
        by_type.setdefault(q["type"], []).append(ok)
    for t, oks in by_type.items():
        print(f"{t:<14} {sum(oks)}/{len(oks)}")

    print("\nMisses (any gold item outside top 5):")
    for q, ranks in results:
        if any(r is None or r > 5 for r in ranks):
            print(f'{q["id"]}: {q["question"]}  -> {ranks}')


if __name__ == "__main__":
    main()