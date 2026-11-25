import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = os.getenv("QUESTIONS_FILE", "questions.jsonl")
FIGURE = re.compile(r"\$?[\d,]*\d(?:\.\d+)?(?:\s(?:million|billion|trillion))?%?")
MAX_DOCS = 8

docs = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "data" / "processed").glob("*/*.txt")}

for line in (ROOT / "evals" / QUESTIONS_FILE).read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    q = json.loads(line)
    if not q["gold"]:
        continue
    gold_sources = {g["source"] for g in q["gold"]}
    print("=" * 70)
    print(q["id"], "|", q["question"])
    print("ANSWER:", q["answer"])
    for fig in dict.fromkeys(FIGURE.findall(q["answer"])):
        others = [(s, t) for s, t in docs.items() if s not in gold_sources and fig in t]
        if not others:
            print(f"  {fig!r}: only in the gold document(s)")
        elif len(others) > MAX_DOCS:
            print(f"  {fig!r}: too common, appears in {len(others)} other documents")
        else:
            print(f"  {fig!r}: also in {len(others)} other document(s):")
            for source, text in others:
                i = text.find(fig)
                snippet = text[max(0, i - 100): i + 100].replace("\n", " ")
                print(f"    {source}: ...{snippet}...")