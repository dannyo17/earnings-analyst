import json
from collections import Counter
from pathlib import Path

from chunking import chunk_text, parse_metadata

PROCESSED = Path("data/processed")
OUT = PROCESSED / "chunks.jsonl"
MIN_CHARS = 5000  # skip boilerplate exhibits (e.g. Amazon's EX-99.2)

if __name__ == "__main__":
    docs_used, skipped, all_chunks = 0, [], []

    for path in sorted(PROCESSED.glob("*/*.txt")):
        text = path.read_text(encoding="utf-8")
        if len(text) < MIN_CHARS:
            skipped.append(path.name)
            continue
        meta = parse_metadata(path)
        for i, chunk in enumerate(chunk_text(text)):
            all_chunks.append(
                {"id": f"{meta['source']}__{i:03d}", "text": chunk, **meta, "chunk_index": i}
            )
        docs_used += 1

    with OUT.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    sizes = [len(c["text"]) for c in all_chunks]
    print(f"Documents used: {docs_used}")
    print(f"Documents skipped (under {MIN_CHARS:,} chars): {len(skipped)}")
    for name in skipped:
        print(f"  skipped: {name}")
    print(f"Total chunks: {len(all_chunks):,}")
    print(f"Total characters: {sum(sizes):,}")
    print(f"Chunk size: min {min(sizes)}, max {max(sizes)}, avg {sum(sizes) // len(sizes)}")
    print("Chunks per company:", dict(Counter(c["ticker"] for c in all_chunks)))