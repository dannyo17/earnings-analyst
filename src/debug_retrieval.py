import json
import sys
from pathlib import Path

from search import retrieve

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


questions = {q["id"]: q for q in load(ROOT / "evals" / "questions.jsonl")}
chunks = load(ROOT / "data" / "processed" / "chunks.jsonl")


def main(qid):
    q = questions[qid]
    print(q["question"])

    # 1. Does any chunk even contain the evidence? (if not, chunking is the problem)
    for g in q["gold"]:
        holders = [c["id"] for c in chunks
                   if c["source"] == g["source"] and g["evidence"] in c["text"]]
        print(f'\nGOLD {g["source"]}: "{g["evidence"]}"')
        print("Chunks containing the evidence:", holders or "NONE (chunking problem)")

    # 2. What did retrieval actually return?
    hits = retrieve(q["question"], k=50)
    print("\nTop 5 returned:")
    for i, h in enumerate(hits[:5], 1):
        print(f'{i}. {h["source"]} chunk {h["chunk_index"]} score {h["score"]:.3f}')
        print("   ", h["text"][:160].replace("\n", " | "))

    # 3. Where does the right chunk sit if we look deeper?
    for g in q["gold"]:
        rank = None
        for i, h in enumerate(hits, 1):
            if h["source"] == g["source"] and g["evidence"] in h["text"]:
                rank = i
                break
        print(f'\nRank of "{g["evidence"][:40]}..." within top 50:', rank)


if __name__ == "__main__":
    main(sys.argv[1])