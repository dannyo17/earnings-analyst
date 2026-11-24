import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(max_retries=5)
col = chromadb.PersistentClient(path="data/chroma").get_collection("filings")
MODEL = "claude-haiku-5-5"
OUT = Path("data/contexts.jsonl")
WORKERS = 8

PROMPT = """You are helping build a search index over SEC filings. Below are the beginning of a document, the text just before a chunk, and the chunk itself.

<document_start>
{head}
</document_start>

<previous_text>
{prev}
</previous_text>

<chunk>
{chunk}
</chunk>

Write 1 to 3 plain sentences (under 70 words) saying where this chunk comes from and what it contains, so a search for it would match. Include: the company, the document type, the period it covers (for example "three months ended September 26, 2026"), the section or statement name, and, if the chunk is a table, what the rows measure and which column is which period. Use only facts visible above. Output only those sentences."""


def load_chunks():
    got = col.get(include=["documents", "metadatas"])
    by_source = {}
    for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"]):
        by_source.setdefault(meta["source"], []).append((meta["chunk_index"], cid, text))
    for source in by_source:
        by_source[source].sort()
    return by_source


def generate(task):
    cid, source, idx, prompt = task
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if not text:
        raise ValueError("empty context")
    return cid, source, idx, text, resp.usage.input_tokens, resp.usage.output_tokens


done = set()
if OUT.exists():
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            done.add(json.loads(line)["id"])

by_source = load_chunks()
tasks = []
total = 0
for source, chunks in by_source.items():
    for i, (idx, cid, text) in enumerate(chunks):
        total += 1
        if cid in done:
            continue
        prompt = PROMPT.format(
            head=chunks[0][2][:1500],
            prev=chunks[i - 1][2][-700:] if i > 0 else "",
            chunk=text,
        )
        tasks.append((cid, source, idx, prompt))

print(f"{total} chunks in index, {len(done)} already done, {len(tasks)} to do")

tin = tout = failed = 0
with OUT.open("a", encoding="utf-8") as f, ThreadPoolExecutor(WORKERS) as pool:
    futures = {pool.submit(generate, t): t for t in tasks}
    for n, fut in enumerate(as_completed(futures), start=1):
        try:
            cid, source, idx, text, i_tok, o_tok = fut.result()
        except Exception as e:
            failed += 1
            t = futures[fut]
            print("FAILED", t[1], t[2], type(e).__name__, str(e)[:120])
            continue
        f.write(json.dumps({"id": cid, "source": source, "chunk_index": idx,
                            "context": text}, ensure_ascii=False) + "\n")
        f.flush()
        tin += i_tok
        tout += o_tok
        if n % 100 == 0:
            print(f"{n}/{len(tasks)} done, {failed} failed, {tin:,} in / {tout:,} out tokens")

print(f"Finished. {failed} failed. Tokens: {tin:,} in / {tout:,} out.")
if failed:
    print("Run the script again to retry the failed chunks.")