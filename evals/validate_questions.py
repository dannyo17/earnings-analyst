import json
from collections import Counter
from pathlib import Path

PROCESSED = Path("data/processed")
TYPES = {
    "recent_fact", "single_fact", "exact_number",
    "cross_company", "multi_section", "unanswerable",
}
FIELDS = ["id", "type", "question", "answer", "gold"]


def find_file(stem):
    matches = list(PROCESSED.glob(f"*/{stem}.txt"))
    return matches[0] if matches else None


errors, seen, types = [], set(), Counter()
lines = Path("evals/questions.jsonl").read_text(encoding="utf-8").splitlines()

for n, line in enumerate(lines, 1):
    if not line.strip():
        continue
    try:
        q = json.loads(line)
    except json.JSONDecodeError as e:
        errors.append(f"line {n}: not valid JSON ({e})")
        continue

    for field in FIELDS:
        if field not in q:
            errors.append(f"line {n}: missing field '{field}'")
    if q.get("id") in seen:
        errors.append(f"line {n}: duplicate id {q.get('id')}")
    seen.add(q.get("id"))

    qtype = q.get("type")
    types[qtype] += 1
    if qtype not in TYPES:
        errors.append(f"line {n}: unknown type '{qtype}'")

    gold = q.get("gold") or []
    if qtype == "unanswerable" and gold:
        errors.append(f"line {n}: unanswerable questions must have an empty gold list")
    if qtype != "unanswerable" and not gold:
        errors.append(f"line {n}: answerable questions need at least one gold entry")

    for g in gold:
        path = find_file(g.get("source", ""))
        if path is None:
            errors.append(f"line {n}: source file not found: {g.get('source')}")
        elif g.get("evidence", "") not in path.read_text(encoding="utf-8"):
            errors.append(f"line {n}: evidence not found in {g['source']}: {g.get('evidence')!r}")

print(f"{len(seen)} questions checked. By type: {dict(types)}")
if errors:
    print(f"\n{len(errors)} problem(s):")
    for e in errors:
        print("  -", e)
else:
    print("No problems found.")