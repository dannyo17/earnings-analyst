import json
from pathlib import Path
from search import retrieve_routed

FAILING = ["q006", "q008", "q015", "q016", "q021", "q025", "q026"]
DEPTH = 150

questions = {}
for line in Path("evals/questions.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        q = json.loads(line)
        questions[q["id"]] = q

for qid in FAILING:
    q = questions[qid]
    hits = retrieve_routed(q["question"], k=DEPTH)
    print("=" * 80)
    print(qid, "|", q["question"])
    print("hit keys:", list(hits[0].keys()), "| hits returned:", len(hits))
    for item in q["gold"]:
        rank = None
        for r, h in enumerate(hits, start=1):
            if item["evidence"] in h["text"] and item["source"] in str(h.get("source", "")):
                rank = r
                break
        print("-" * 80)
        print("GOLD:", item["source"], "|", item["evidence"][:70])
        print("RANK:", rank if rank else f"not in top {DEPTH}")
        if rank is None or rank > 5:
            for h in hits[:3]:
                print("  beat it:", h.get("source"), "|", h["text"][:100].replace("\n", " "))