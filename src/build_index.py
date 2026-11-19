import json
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS = Path("data/processed/chunks.jsonl")
DB_DIR = "data/chroma"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
BATCH = 64

if __name__ == "__main__":
    lines = CHUNKS.read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(line) for line in lines]

    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=DB_DIR)

    # Start fresh so reruns never mix old and new data
    try:
        client.delete_collection("filings")
    except Exception:
        pass
    collection = client.create_collection("filings", metadata={"hnsw:space": "cosine"})

    start = time.time()
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        embeddings = model.encode([c["text"] for c in batch], normalize_embeddings=True)
        collection.add(
            ids=[c["id"] for c in batch],
            embeddings=embeddings.tolist(),
            documents=[c["text"] for c in batch],
            metadatas=[
                {
                    "ticker": c["ticker"],
                    "doc_type": c["doc_type"],
                    "date": c["date"],
                    "source": c["source"],
                    "chunk_index": c["chunk_index"],
                }
                for c in batch
            ],
        )
        print(f"embedded {min(i + BATCH, len(chunks)):,} / {len(chunks):,}")

    elapsed = time.time() - start
    print(f"Done: {collection.count():,} chunks in {elapsed:.0f} seconds")