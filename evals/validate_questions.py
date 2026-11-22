import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_TYPES = {"recent_fact", "single_fact", "exact_number",
                 "cross_company", "multi_section", "unanswerable"}
REQUIRED = ["id", "type", "question", "answer", "gold"]

_text_cache = {}


def source_text(stem):
    """Return the text of data/processed/<TICKER>/<stem>.txt, or None if missing."""
    if stem not in _text_cache:
        matches = list((ROOT / "data" / "processed").glob(f"*/{stem}.txt"))
        _text_cache[stem] = matches[0].read_text(encoding="utf-8") if matches else None
    return _text_cache[stem]


def check_item(n, item, label, errors):
    if not isinstance(item, dict) or "source" not in item or "evidence" not in item:
        errors.append(f"line {n}: {label} needs 'source' and 'evidence'")
        return
    text = source_text(item["source"])
    if text is None:
        errors.append(f"line {n}: {label} source file not found: {item['source']}")
    elif item["evidence"] not in text:
        errors.append(f"line {n}: {label} evidence not found in {item['source']}: {item['evidence']!r}")


lines = (ROOT / "evals" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
errors = []
seen = set()
types = Counter()

for n, line in enumerate(lines, start=1):
    if not line.strip():
        continue
    try:
        q = json.loads(line)
    except json.JSONDecodeError as e:
        errors.append(f"line {n}: invalid JSON ({e})")
        continue

    missing = [k for k in REQUIRED if k not in q]
    if missing:
        errors.append(f"line {n}: missing fields {missing}")
        continue

    if q["id"] in seen:
        errors.append(f"line {n}: duplicate id {q['id']}")
    seen.add(q["id"])

    if q["type"] not in ALLOWED_TYPES:
        errors.append(f"line {n}: unknown type {q['type']!r}")
    types[q["type"]] += 1

    if q["type"] == "unanswerable":
        if q["gold"]:
            errors.append(f"line {n}: unanswerable questions must have an empty gold list")
    elif not q["gold"]:
        errors.append(f"line {n}: answerable questions need at least one gold entry")

    for g in q["gold"]:
        check_item(n, g, "gold", errors)
        for alt in g.get("also_accept", []) if isinstance(g, dict) else []:
            check_item(n, alt, "also_accept", errors)

print(f"{len(seen)} questions checked. By type: {dict(types)}")
if errors:
    print(f"\n{len(errors)} problem(s):")
    for e in errors:
        print("  -", e)
else:
    print("No problems found.")