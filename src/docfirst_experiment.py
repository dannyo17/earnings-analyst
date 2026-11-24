import json
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from search import retrieve_routed, MODEL_NAME
from eval_retrieval import first_rank

PREFIX = "Represent this sentence for searching relevant passages: "
RRF_K = 60

col = chromadb.PersistentClient(path="data/chroma").get_collection("filings")
model = SentenceTransformer(MODEL_NAME)


def tokens(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def pick_docs(question, per_ticker):
    hits = retrieve_routed(question, k=40)
    docs, count = [], {}
    for h in hits:
        if h["source"] in docs or count.get(h["ticker"], 0) >= per_ticker:
            continue
        docs.append(h["source"])
        count[h["ticker"]] = count.get(h["ticker"], 0) + 1
    return docs


def rank_in_doc(question, source, qvec):
    n = len(col.get(where={"source": source}, include=[])["ids"])
    if n == 0:
        print("WARNING: no chunks found for", source)
        return []
    res = col.query(query_embeddings=[qvec], n_results=n,
                    where={"source": source}, include=["documents"])
    texts = res["documents"][0]  # already in vector-similarity order
    scores = BM25Okapi([tokens(t) for t in texts]).get_scores(tokens(question))
    bm_order = sorted(range(len(texts)), key=lambda i: -scores[i])
    fused = {i: 1 / (RRF_K + i + 1) for i in range(len(texts))}
    for r, i in enumerate(bm_order):
        fused[i] += 1 / (RRF_K + r + 1)
    best = sorted(fused, key=lambda i: -fused[i])
    return [{"text": texts[i], "source": source} for i in best]


def docfirst(question, per_ticker, per_doc, k=10):
    docs = pick_docs(question, per_ticker)
    qvec = model.encode(PREFIX + question, normalize_embeddings=True).tolist()
    lists = [rank_in_doc(question, d, qvec)[:per_doc] for d in docs]
    out = []
    for i in range(per_doc):
        for lst in lists:
            if i < len(lst):
                out.append(lst[i])
    return out[:k]


def evaluate(name, retriever, questions):
    all_ranks = []
    full = {}
    for q in questions:
        hits = retriever(q["question"])
        ranks = [first_rank(hits, g) for g in q["gold"]]
        all_ranks += ranks
        full[q["id"]] = all(r is not None and r <= 5 for r in ranks)
    found = sum(1 for r in all_ranks if r is not None and r <= 5)
    mrr = sum(1 / r for r in all_ranks if r) / len(all_ranks)
    print(f"{name:28s} Recall@5 {found}/{len(all_ranks)} ({found / len(all_ranks):.0%})  "
          f"MRR {mrr:.3f}  full-hit@5 {sum(full.values())}/{len(full)}")
    return full

questions = []
for line in Path("evals/questions.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        q = json.loads(line)
        if q["gold"]:
            questions.append(q)

base = evaluate("routed (current)", lambda s: retrieve_routed(s, k=10), questions)
for per_ticker, per_doc in [(2, 3), (3, 2)]:
    name = f"doc-first docs={per_ticker} chunks={per_doc}"
    res = evaluate(name, lambda s: docfirst(s, per_ticker, per_doc), questions)
    gained = [i for i in res if res[i] and not base[i]]
    lost = [i for i in res if base[i] and not res[i]]
    print("   gained:", gained, " lost:", lost)