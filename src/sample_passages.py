import random
from pathlib import Path

import chromadb

SEED = 2026
N = 40

col = chromadb.PersistentClient(path="data/chroma").get_collection("filings")
got = col.get(include=["documents", "metadatas"])

by_ticker = {}
for meta, text in zip(got["metadatas"], got["documents"]):
    by_ticker.setdefault(meta["ticker"], []).append((meta, text))

random.seed(SEED)
tickers = sorted(by_ticker)
lines = []
for n in range(N):
    meta, text = random.choice(by_ticker[tickers[n % len(tickers)]])
    lines.append("=" * 70)
    lines.append(f"#{n + 1} | {meta['source']} | chunk {meta['chunk_index']}")
    lines.append(text)

Path("data/heldout_passages.txt").write_text("\n".join(lines), encoding="utf-8")
print("Wrote data/heldout_passages.txt with", N, "passages")