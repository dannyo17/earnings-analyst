import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

chunks_by_source = {}
with open(ROOT / "data" / "processed" / "chunks.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            chunk = json.loads(line)
            chunks_by_source.setdefault(chunk["source"], []).append(chunk["text"])

with open(ROOT / "evals" / "questions.jsonl", encoding="utf-8") as f:
    questions = [json.loads(line) for line in f if line.strip()]

total, missing = 0, []
for q in questions:
    for gold in q["gold"]:
        options = [(gold["source"], gold["evidence"])]
        options += [(a["source"], a["evidence"]) for a in gold.get("also_accept", [])]
        for source, evidence in options:
            total += 1
            if not any(evidence in text for text in chunks_by_source.get(source, [])):
                missing.append((q["id"], source, evidence))

print(f"{len(chunks_by_source)} sources, {sum(len(v) for v in chunks_by_source.values())} chunks")
print(f"Evidence strings checked: {total}; not found inside a single chunk: {len(missing)}")
for item in missing:
    print("  MISSING:", item)