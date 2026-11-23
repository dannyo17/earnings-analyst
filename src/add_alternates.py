import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "evals" / "questions.jsonl"

# (question id, start of the gold item's source, alternate source, alternate evidence)
ADDITIONS = [
    ("q013", "AMD", "AMD_8-K_EX-99.1_2026-11-03",
     "Data Center segment revenue was a record $8.5 billion"),
    ("q013", "AMD", "AMD_8-K_EX-99.2_2026-11-03",
     "Data Center Segment Revenue $4.3B $8.5B"),
    ("q013", "AMD", "AMD_10-Q_2026-09-26",
     "Data Center net revenue of $8.5 billion for the three months ended September 26, 2026"),
    ("q020", "NVDA", "NVDA_10-K_2026-01-25",
     "Total revenue | 215,938 | 130,497 | 60,922"),
    ("q020", "NVDA", "NVDA_8-K_EX-99.1_2026-02-25",
     "Revenue | $215,938 | $130,497 | 65%"),
    ("q024", "NVDA", "NVDA_8-K_EX-99.1_2026-08-26",
     "returned approximately $26.0 billion to shareholders"),
    ("q027", "MSFT", "MSFT_10-Q_2026-09-30",
     "Azure | 33,165 | 22,384"),
    ("q027", "MSFT", "MSFT_8-K_EX-99.1_2026-10-28",
     "Azure | $33,165 | $22,384"),
    ("q027", "AMZN", "AMZN_8-K_EX-99.1_2026-10-29",
     "AWS net sales increased 39.3%"),
]

raw = PATH.read_bytes()
eol = "\r\n" if b"\r\n" in raw else "\n"  # keep the file's existing line endings
text = raw.decode("utf-8")
questions = [json.loads(line) for line in text.splitlines() if line.strip()]
by_id = {q["id"]: q for q in questions}

for qid, prefix, source, evidence in ADDITIONS:
    items = [g for g in by_id[qid]["gold"] if g["source"].startswith(prefix)]
    if len(items) != 1:
        raise SystemExit(
            f"{qid}: expected exactly one gold item starting with {prefix}, found {len(items)}"
        )
    alternates = items[0].setdefault("also_accept", [])
    new = {"source": source, "evidence": evidence}
    if new not in alternates:
        alternates.append(new)

out = eol.join(json.dumps(q, ensure_ascii=False) for q in questions) + eol
PATH.write_bytes(out.encode("utf-8"))
print("Added alternates to:", sorted({a[0] for a in ADDITIONS}))