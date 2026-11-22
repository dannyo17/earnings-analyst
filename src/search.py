import math
import re
import sys

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Words that tell us which company a question is about (matched as whole words, lowercase)
COMPANY_KEYWORDS = {
    "NVDA": ["nvidia", "nvda"],
    "AMD": ["amd", "advanced micro devices"],
    "MSFT": ["microsoft", "msft", "azure"],
    "AMZN": ["amazon", "amzn", "aws"],
}

model = SentenceTransformer(MODEL_NAME)
collection = chromadb.PersistentClient(path="data/chroma").get_collection("filings")


def _query(query_vec, n, where=None):
    """Ask the vector database for the n closest chunks, optionally limited by metadata."""
    result = collection.query(
        query_embeddings=[query_vec.tolist()], n_results=n, where=where
    )
    hits = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append({"text": doc, "score": 1 - dist, **meta})
    return hits


def retrieve(question, k=5):
    """Baseline: return the k chunks closest in meaning to the question."""
    query_vec = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    return _query(query_vec, k)


def detect_companies(question):
    """Which of our four companies does the question mention?"""
    text = question.lower()
    found = []
    for ticker, words in COMPANY_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", text) for w in words):
            found.append(ticker)
    return found


def retrieve_routed(question, k=5):
    """Company-aware retrieval: search only the named companies' chunks."""
    companies = detect_companies(question)
    if not companies:
        return retrieve(question, k)

    query_vec = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    per_company = math.ceil(k / len(companies))
    lists = [_query(query_vec, per_company, where={"ticker": t}) for t in companies]

    # Interleave so each company gets a fair share of the top ranks
    merged = []
    for rank in range(per_company):
        for hits in lists:
            if rank < len(hits):
                merged.append(hits[rank])
    return merged[:k]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    for rank, hit in enumerate(retrieve(question), 1):
        print(f"\n#{rank}  score {hit['score']:.3f}  {hit['ticker']} {hit['doc_type']} {hit['date']}")
        print(hit["text"][:300].replace("\n", " "))