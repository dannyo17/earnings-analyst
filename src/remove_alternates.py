import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "evals" / "questions.jsonl"

# (question id, alternate source, alternate evidence) to remove:
# these alternates state the figure less precisely than the reference answer
REMOVALS = [
    ("q008", "AMZN_8-K_EX-99.1_2026-10-29",
     "Net sales increased 12% to $201.9 billion in the third quarter"),
    ("q015", "MSFT_8-K_EX-99.1_2026-10-28",
     "Revenue was $92.3 billion and increased 19%"),
]

raw = PATH.read_bytes()
eol = "\r\n" if b"\r\n" in raw else "\n"
questions = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
by_id = {q["id"]: q for q in questions}

for qid, source, evidence in REMOVALS:
    removed = 0
    for gold in by_id[qid]["gold"]:
        alternates = gold.get("also_accept", [])
        kept = [a for a in alternates
                if not (a["source"] == source and a["evidence"] == evidence)]
        removed += len(alternates) - len(kept)
        if kept:
            gold["also_accept"] = kept
        else:
            gold.pop("also_accept", None)
    if removed != 1:
        raise SystemExit(f"{qid}: expected to remove exactly 1 alternate, removed {removed}")

out = eol.join(json.dumps(q, ensure_ascii=False) for q in questions) + eol
PATH.write_bytes(out.encode("utf-8"))
print("Removed alternates from:", sorted({r[0] for r in REMOVALS}))