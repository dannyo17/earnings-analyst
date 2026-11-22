import json
import re
import sys
import time
from pathlib import Path

from answer import answer
from llm import ask_llm

ROOT = Path(__file__).resolve().parent.parent
RETRIEVAL = sys.argv[1] if len(sys.argv) > 1 else "routed"
K = 5
JUDGE_MODEL = "claude-sonnet-5-5"

# Same model as the RAG system, but with no documents at all
BASELINE_SYSTEM = (
    "You are a financial analyst. Answer the question concisely. "
    "If you do not know the answer, reply exactly: I don't know."
)

JUDGE_SYSTEM = (
    "You grade answers to questions about company earnings. You are given a question, "
    "a reference answer and a candidate answer. Reply with exactly one word:\n"
    "correct - the candidate states the same fact or figure as the reference "
    "(rounding or formatting differences are fine, extra correct context is fine, "
    "but it must not contradict the reference).\n"
    "refused - the candidate says it does not know or cannot answer.\n"
    "incorrect - the candidate gives an answer that differs from or contradicts the "
    "reference, or states wrong figures.\n"
    "If the reference answer is itself a refusal (\"I don't know...\"), a candidate "
    "that refuses is 'refused' and a candidate that gives any specific answer is "
    "'incorrect'."
)


def load_questions():
    with open(ROOT / "evals" / "questions.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def judge(question, reference, candidate):
    user = f"Question: {question}\nReference answer: {reference}\nCandidate answer: {candidate}"
    text = ask_llm(JUDGE_SYSTEM, user, max_tokens=1024, model=JUDGE_MODEL)["text"]
    match = re.search(r"\b(incorrect|correct|refused)\b", text.lower())
    if match:
        return match.group(1)
    print(f"  [judge reply could not be read: {text!r}]")
    return "unparsed"


def gold_options(gold):
    options = [(gold["source"], gold["evidence"])]
    options += [(a["source"], a["evidence"]) for a in gold.get("also_accept", [])]
    return options


def supported_by(hits, gold):
    """True if any of these chunks contains acceptable evidence for the gold item."""
    return any(
        hit["source"] == source and evidence in hit["text"]
        for hit in hits
        for source, evidence in gold_options(gold)
    )


def cited_hits(text, hits):
    """The chunks the answer cites, e.g. [1], [2] or [1, 3]."""
    numbers = set()
    for group in re.findall(r"\[([\d,\s]+)\]", text):
        numbers.update(int(n) for n in re.findall(r"\d+", group))
    return [hits[n - 1] for n in sorted(numbers) if 1 <= n <= len(hits)]


def short(text, n=300):
    text = text.replace("\n", " ")
    return text if len(text) <= n else text[:n] + "..."


def main():
    print(f"Retrieval mode: {RETRIEVAL}, k={K}, judge: {JUDGE_MODEL}\n")
    rows = []
    for q in load_questions():
        start = time.time()
        rag, hits = answer(q["question"], k=K, retrieval=RETRIEVAL)
        rag_seconds = time.time() - start
        base = ask_llm(BASELINE_SYSTEM, q["question"])

        rag_verdict = judge(q["question"], q["answer"], rag["text"])
        base_verdict = judge(q["question"], q["answer"], base["text"])

        answerable = bool(q["gold"])
        retrieved_ok = answerable and all(supported_by(hits, g) for g in q["gold"])
        cited = cited_hits(rag["text"], hits)
        cited_ok = answerable and all(supported_by(cited, g) for g in q["gold"])

        rows.append({
            "id": q["id"], "type": q["type"], "question": q["question"],
            "reference": q["answer"], "answerable": answerable,
            "rag_answer": rag["text"], "rag_verdict": rag_verdict,
            "base_answer": base["text"], "base_verdict": base_verdict,
            "retrieved_ok": retrieved_ok, "cited_ok": cited_ok,
            "rag_seconds": rag_seconds,
            "rag_in": rag["input_tokens"], "rag_out": rag["output_tokens"],
        })
        print(f'{q["id"]}  {q["type"]:<14} rag={rag_verdict:<10} no-retrieval={base_verdict:<10} '
              f'retrieved_ok={retrieved_ok}  cited_ok={cited_ok}')

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]

    def count(rs, key, value):
        return sum(1 for r in rs if r[key] == value)

    n = len(answerable)
    print(f"\nAnswerable questions ({n})")
    for label, key in (("RAG", "rag_verdict"), ("No retrieval", "base_verdict")):
        print(f"  {label:<13} correct {count(answerable, key, 'correct')}/{n}   "
              f"incorrect {count(answerable, key, 'incorrect')}   "
              f"refused {count(answerable, key, 'refused')}")

    m = len(unanswerable)
    print(f"\nUnanswerable questions ({m}): correctly refused")
    print(f"  RAG {count(unanswerable, 'rag_verdict', 'refused')}/{m}   "
          f"No retrieval {count(unanswerable, 'base_verdict', 'refused')}/{m}")

    correct_rag = [r for r in answerable if r["rag_verdict"] == "correct"]
    print(f"\nCitation accuracy: {sum(r['cited_ok'] for r in correct_rag)}/{len(correct_rag)} "
          f"of RAG's correct answers cite a passage containing the gold evidence")
    retrieved = [r for r in answerable if r["retrieved_ok"]]
    print(f"Retrieval reached all gold evidence in top {K}: {len(retrieved)}/{n}; "
          f"of those, answered correctly: {sum(r['rag_verdict'] == 'correct' for r in retrieved)}/{len(retrieved)}")

    print(f"\nAverage RAG time: {sum(r['rag_seconds'] for r in rows) / len(rows):.2f} s per question")
    print(f"Average RAG tokens: {sum(r['rag_in'] for r in rows) / len(rows):.0f} in, "
          f"{sum(r['rag_out'] for r in rows) / len(rows):.0f} out")

    print("\nRAG answers to review (anything that is not correct / correctly refused):")
    for r in rows:
        ok = r["rag_verdict"] == ("correct" if r["answerable"] else "refused")
        if not ok:
            print(f'\n{r["id"]} [{r["rag_verdict"]}] {r["question"]}')
            print(f'  reference: {short(r["reference"])}')
            print(f'  RAG said:  {short(r["rag_answer"])}')

    out_dir = ROOT / "evals" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"answers_{RETRIEVAL}.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()