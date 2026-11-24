import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CONTEXTS = Path("data/contexts.jsonl")

client = chromadb.PersistentClient(path="data/chroma")
old = client.get_collection("filings")
got = old.get(include=["documents", "metadatas"])
ids, texts, metas = got["ids"], got["documents"], got["metadatas"]
print("chunks in current index:", len(ids))

contexts = {}
for line in CONTEXTS.read_text(encoding="utf-8").splitlines():
    if line.strip():
        row = json.loads(line)
        contexts[row["id"]] = row["context"]
missing = [i for i in ids if i not in contexts]
assert not missing, f"{len(missing)} chunks have no context"

enriched = [contexts[i] + "\n\n" + t for i, t in zip(ids, texts)]

model = SentenceTransformer(MODEL_NAME)
limit = model.max_seq_length


def token_counts(batch):
    enc = model.tokenizer(batch, add_special_tokens=True, truncation=False)
    return [len(x) for x in enc["input_ids"]]


plain_over = sum(1 for n in token_counts(texts) if n > limit)
ctx_over = sum(1 for n in token_counts(enriched) if n > limit)
print(f"Model limit: {limit} tokens. Chunks over the limit: "
      f"{plain_over} plain, {ctx_over} with context")

embeddings = model.encode(enriched, batch_size=32, show_progress_bar=True,
                          normalize_embeddings=True)

client.delete_collection("filings")
new = client.create_collection("filings", metadata={"hnsw:space": "cosine"})
for start in range(0, len(ids), 500):
    end = start + 500
    new.add(ids=ids[start:end], documents=texts[start:end],
            metadatas=metas[start:end], embeddings=embeddings[start:end].tolist())
print("New index size:", new.count())