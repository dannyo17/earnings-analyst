import json
from pathlib import Path

FAILING = ["q006", "q008", "q015", "q016", "q021", "q025", "q026"]
WINDOW = 300

questions = {}
for line in Path("evals/questions.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        q = json.loads(line)
        questions[q["id"]] = q

for qid in FAILING:
    q = questions[qid]
    print("=" * 80)
    print(qid, "|", q["question"])
    print("REFERENCE:", q["answer"])
    for item in q["gold"]:
        source = item["source"]
        evidence = item["evidence"]
        files = list(Path("data/processed").glob(f"*/{source}*"))
        print("-" * 80)
        print("SOURCE:", source, "| files found:", len(files))
        if not files:
            continue
        text = files[0].read_text(encoding="utf-8")
        i = text.find(evidence)
        print("EVIDENCE:", evidence)
        print("CONTEXT:")
        print(text[max(0, i - WINDOW): i + len(evidence) + WINDOW])