import sys

from llm import ask_llm
from search import retrieve

SYSTEM = (
    "You are an AI research analyst answering questions about company earnings "
    "releases and SEC filings. Answer using ONLY the numbered context passages "
    "provided. Cite every claim with the passage number in square brackets, "
    "like [2]. Each passage is labeled with its company, document type and date, "
    "so pay attention to which quarter a passage covers. If the passages do not "
    "contain the answer, reply exactly: I don't know based on the provided "
    "documents. Never use outside knowledge. Quote figures exactly as written."
)


def answer(question, k=5):
    hits = retrieve(question, k)
    context = "\n\n".join(
        f"[{i}] ({h['ticker']}, {h['doc_type']}, {h['date']})\n{h['text']}"
        for i, h in enumerate(hits, 1)
    )
    user = f"Context passages:\n\n{context}\n\nQuestion: {question}"
    return ask_llm(SYSTEM, user), hits


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    result, hits = answer(question)
    print(result["text"])
    print("\nSources:")
    for i, h in enumerate(hits, 1):
        print(f"[{i}] {h['ticker']} {h['doc_type']} {h['date']}")
    print(f"\n(tokens: {result['input_tokens']} in, {result['output_tokens']} out)")