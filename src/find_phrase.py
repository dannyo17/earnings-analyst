import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_MATCHES = 12

docs = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "data" / "processed").glob("*/*.txt")}

for pattern in sys.argv[1:]:
    rx = re.compile(pattern, re.IGNORECASE)
    print("=" * 70)
    print("PATTERN:", pattern)
    shown = 0
    for source, text in docs.items():
        m = rx.search(text)
        if m:
            shown += 1
            if shown <= MAX_MATCHES:
                snippet = text[max(0, m.start() - 100): m.end() + 100].replace("\n", " ")
                print(f"  {source}: ...{snippet}...")
    print(f"  ({shown} document(s) match)")