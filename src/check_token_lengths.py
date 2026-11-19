import json
from pathlib import Path

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
tokenizer = model.tokenizer

lines = Path("data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
chunks = [json.loads(line) for line in lines]
lengths = [len(tokenizer.encode(c["text"])) for c in chunks]

ordered = sorted(lengths)
print(f"Chunks: {len(lengths):,}")
print(f"Tokens per chunk: avg {sum(lengths) // len(lengths)}, "
      f"95th percentile {ordered[int(0.95 * len(ordered))]}, max {ordered[-1]}")
print(f"Over 256 tokens: {sum(n > 256 for n in lengths):,}")
print(f"Over 512 tokens: {sum(n > 512 for n in lengths):,}")