import json
from pathlib import Path

lines = Path("data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
chunks = [json.loads(line) for line in lines]

tiny = [c for c in chunks if len(c["text"]) < 200]
huge = [c for c in chunks if len(c["text"]) > 2500]
print(f"Chunks under 200 chars: {len(tiny)}")
print(f"Chunks over 2,500 chars: {len(huge)}")

print("\n--- 5 smallest ---")
for c in sorted(chunks, key=lambda c: len(c["text"]))[:5]:
    print(len(c["text"]), c["id"], ascii(c["text"][:150]))

print("\n--- 3 largest ---")
for c in sorted(chunks, key=lambda c: len(c["text"]), reverse=True)[:3]:
    print(len(c["text"]), c["id"], ascii(c["text"][:200]))