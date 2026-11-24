import math
import re
import sys
import json
import datetime
from pathlib import Path
from rank_bm25 import BM25Okapi

import chromadb
from sentence_transformers import CrossEncoder, SentenceTransformer

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

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None


def retrieve_reranked(question, k=5, candidates=50):
    """Fetch a wide candidate pool with company-aware search, then re-score it with a cross-encoder."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL)
    pool = retrieve_routed(question, candidates)
    scores = _reranker.predict([(question, hit["text"]) for hit in pool])
    ranked = sorted(zip(pool, scores), key=lambda pair: pair[1], reverse=True)
    return [{**hit, "score": float(score)} for hit, score in ranked][:k]

ROOT = Path(__file__).resolve().parent.parent
RRF_K = 60

_chunks = None
_bm25 = None


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _lexical(question, n):
    """The n chunks whose words best match the question's words (BM25)."""
    global _chunks, _bm25
    if _bm25 is None:
        with open(ROOT / "data" / "processed" / "chunks.jsonl", encoding="utf-8") as f:
            _chunks = [json.loads(line) for line in f if line.strip()]
        _bm25 = BM25Okapi([_tokens(c["text"]) for c in _chunks])
    scores = _bm25.get_scores(_tokens(question))
    best = sorted(range(len(_chunks)), key=lambda i: scores[i], reverse=True)[:n]
    return [_chunks[i] for i in best]


def retrieve_hybrid(question, k=5, candidates=50):
    """Merge the meaning-based (vector) and word-based (BM25) rankings with reciprocal rank fusion."""
    vector_hits = retrieve(question, candidates)
    lexical_hits = _lexical(question, candidates)
    fused = {}
    for hits in (vector_hits, lexical_hits):
        for rank, hit in enumerate(hits, start=1):
            key = (hit["source"], hit["chunk_index"])
            entry = fused.setdefault(key, {"hit": hit, "score": 0.0})
            entry["score"] += 1 / (RRF_K + rank)
    ranked = sorted(fused.values(), key=lambda e: e["score"], reverse=True)
    return [{**e["hit"], "score": e["score"]} for e in ranked[:k]]

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
DATE_RE = re.compile(r"\b(" + "|".join(MONTHS) + r") (\d{1,2}), (\d{4})\b", re.IGNORECASE)
WINDOW_DAYS = 60

_doc_dates = None


def _all_doc_dates():
    """Every distinct document date in the index, e.g. '2026-09-30'."""
    global _doc_dates
    if _doc_dates is None:
        metadatas = collection.get(include=["metadatas"])["metadatas"]
        _doc_dates = sorted({m["date"] for m in metadatas})
    return _doc_dates


def dates_in_window(question):
    """Document dates falling within WINDOW_DAYS after any calendar date the question names."""
    valid = set()
    for month, day, year in DATE_RE.findall(question):
        try:
            named = datetime.date(int(year), MONTHS.index(month.lower()) + 1, int(day))
        except ValueError:
            continue
        for doc_date in _all_doc_dates():
            d = datetime.date.fromisoformat(doc_date)
            if named <= d <= named + datetime.timedelta(days=WINDOW_DAYS):
                valid.add(doc_date)
    return sorted(valid)


def retrieve_dated(question, k=5):
    """Company-aware retrieval that also keeps only documents dated shortly after the period named."""
    valid_dates = dates_in_window(question)
    if not valid_dates:
        return retrieve_routed(question, k)

    companies = detect_companies(question) or [None]
    query_vec = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    per_company = math.ceil(k / len(companies))
    lists = []
    for ticker in companies:
        conditions = [{"date": {"$in": valid_dates}}]
        if ticker:
            conditions.append({"ticker": ticker})
        where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
        lists.append(_query(query_vec, per_company, where=where))

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