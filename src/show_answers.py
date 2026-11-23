import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
mode = "routed"

rows = json.loads(
    (ROOT / "evals" / "results" / f"answers_{mode}.json").read_text(encoding="utf-8")
)

wanted = set(sys.argv[1:])
for r in rows:
    if r["id"] in wanted:
        print("=" * 70)
        print(r["id"], r["type"], "| verdict:", r["rag_verdict"],
              "| retrieved_ok:", r["retrieved_ok"])
        print("Q:        ", r["question"])
        print("Reference:", r["reference"])
        print("RAG said: ", r["rag_answer"])