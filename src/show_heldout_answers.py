import json
import sys

with open("evals/results/answers_routed_heldout.json", encoding="utf-8") as f:
    rows = json.load(f)

for r in rows:
    if r["id"] in sys.argv[1:]:
        print("=" * 70)
        print(r["id"], r["rag_verdict"], "|", r["question"])
        print("REFERENCE:", r["reference"])
        print("APP SAID: ", r["rag_answer"])