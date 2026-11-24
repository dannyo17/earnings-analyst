import json
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
col = chromadb.PersistentClient(path="data/chroma").get_collection("filings")
MODEL = "claude-haiku-5-5"

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

# (question id, index of the gold item) for chunks we know are hard to retrieve
TESTS = [("q006", 0), ("q008", 0), ("q021", 1), ("q025", 0), ("q026", 1)]


def doc_chunks(source):
    got = col.get(where={"source": source}, include=["documents", "metadatas"])
    pairs = sorted(zip(got["metadatas"], got["documents"]), key=lambda p: p[0]["chunk_index"])
    return [text for _, text in pairs]


questions = {}
for line in Path("evals/questions.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        q = json.loads(line)
        questions[q["id"]] = q

total_in = total_out = 0
for qid, gi in TESTS:
    gold = questions[qid]["gold"][gi]
    chunks = doc_chunks(gold["source"])
    idx = next((i for i, c in enumerate(chunks) if gold["evidence"] in c), None)
    print("=" * 70)
    print(qid, "|", gold["source"], "| chunk index in doc:", idx, "of", len(chunks))
    if idx is None:
        print("evidence not inside a single chunk")
        continue
    prompt = PROMPT.format(
        head=chunks[0][:1500],
        prev=chunks[idx - 1][-700:] if idx > 0 else "",
        chunk=chunks[idx],
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    total_in += resp.usage.input_tokens
    total_out += resp.usage.output_tokens
    print("CHUNK STARTS:", chunks[idx][:150].replace("\n", " "))
    text = "".join(b.text for b in resp.content if b.type == "text")
    print("CONTEXT:", text)
    print("tokens in/out:", resp.usage.input_tokens, resp.usage.output_tokens)

n = len(TESTS)
print("=" * 70)
print(f"Average per chunk: {total_in / n:.0f} in, {total_out / n:.0f} out")
print(f"For 3,408 chunks: about {total_in / n * 3408 / 1e6:.2f}M input tokens, "
      f"{total_out / n * 3408 / 1e6:.2f}M output tokens")