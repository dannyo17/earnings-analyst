import sys

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

model = SentenceTransformer(MODEL_NAME)
collection = chromadb.PersistentClient(path="data/chroma").get_collection("filings")


def retrieve(question, k=5):
    """Return the k chunks closest in meaning to the question."""
    query_vec = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    result = collection.query(query_embeddings=[query_vec.tolist()], n_results=k)
    hits = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append({"text": doc, "score": 1 - dist, **meta})
    return hits


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    for rank, hit in enumerate(retrieve(question), 1):
        print(f"\n#{rank}  score {hit['score']:.3f}  {hit['ticker']} {hit['doc_type']} {hit['date']}")
        print(hit["text"][:300].replace("\n", " "))