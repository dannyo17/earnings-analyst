import json
from pathlib import Path

PATH = Path("evals/heldout.jsonl")

ALTERNATES = {
    "h001": [
        ("AMD_10-Q_2026-03-28", "we incurred approximately $440 million of net inventory and related charges in 2025"),
        ("AMD_10-Q_2026-06-27", "we incurred approximately $440 million of net inventory and related charges in 2025"),
        ("AMD_8-K_EX-99.1_2026-02-03", "approximately $440 million in net inventory and related charges"),
        ("AMD_8-K_EX-99.2_2026-02-03", "~$440 million in net inventory and related charges"),
    ],
    "h002": [
        ("MSFT_10-K_2026-06-30", "the IRS is seeking an additional tax payment of $28.9 billion plus penalties and interest"),
        ("MSFT_10-Q_2025-12-31", "the IRS is seeking an additional tax payment of $28.9 billion plus penalties and interest"),
        ("MSFT_10-Q_2026-09-30", "the IRS is seeking an additional tax payment of $28.9 billion plus penalties and interest"),
    ],
    "h003": [
        ("NVDA_10-Q_2026-04-26", "we increased our quarterly cash dividend from $0.01 per share to $0.25 per share"),
        ("NVDA_10-Q_2026-07-26", "we increased our quarterly cash dividend from $0.01 per share to $0.25 per share"),
        ("NVDA_8-K_EX-99.2_2026-05-20", "approved an increase to our quarterly dividend from $0.01 per share to $0.25 per share"),
    ],
    "h008": [
        ("NVDA_8-K_EX-99.1_2026-05-20", "NVIDIA expects GAAP and non-GAAP tax rates to be between 16.0% and 18.0%"),
        ("NVDA_8-K_EX-99.1_2026-08-26", "NVIDIA expects GAAP and non-GAAP tax rates to be between 16.0% and 18.0%"),
        ("NVDA_8-K_EX-99.2_2026-05-20", "we expect GAAP and non-GAAP tax rates to be between 16.0% and 18.0%"),
        ("NVDA_8-K_EX-99.2_2026-08-26", "we expect GAAP and non-GAAP tax rates to be between 16.0% and 18.0%"),
        ("NVDA_8-K_EX-99.2_2026-11-17", "we expect GAAP and non-GAAP tax rates to be between 16.0% and 18.0%"),
    ],
    "h013": [
        ("NVDA_8-K_EX-99.1_2026-11-17", "the company had approximately $227.3 billion remaining under its share repurchase authorization"),
    ],
        "h016": [
        ("AMD_10-K_2025-12-27", "Embedded net revenue of $3.5 billion decreased by 3%"),
    ],
}

out = []
added = 0
for line in PATH.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    q = json.loads(line)
    for source, evidence in ALTERNATES.get(q["id"], []):
        existing = q["gold"][0].setdefault("also_accept", [])
        if not any(a["source"] == source and a["evidence"] == evidence for a in existing):
            existing.append({"source": source, "evidence": evidence})
            added += 1
    out.append(json.dumps(q, ensure_ascii=False))

PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
print("Alternates added:", added)