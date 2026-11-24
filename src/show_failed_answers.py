import json

with open("evals/results/answers_routed.json", encoding="utf-8") as f:
    data = json.load(f)
rows = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))

for r in rows:
    if r["rag_verdict"] != "correct" and r["reference"] != "I don't know based on the provided documents.":
        print("=" * 70)
        print(r["id"], "|", r["question"])
        print("REFERENCE:", r["reference"])
        print("APP SAID: ", r["rag_answer"])
        print("VERDICT:  ", r["rag_verdict"])