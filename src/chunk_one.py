from pathlib import Path

from chunking import chunk_text, parse_metadata

path = Path("data/processed/MSFT/MSFT_8-K_EX-99.1_2026-10-28.txt")
text = path.read_text(encoding="utf-8")

chunks = chunk_text(text)
sizes = [len(c) for c in chunks]

print(parse_metadata(path))
print(f"{len(chunks)} chunks; sizes: min {min(sizes)}, max {max(sizes)}, avg {sum(sizes) // len(sizes)}")
print("--- chunk 3 ---")
print(chunks[2])