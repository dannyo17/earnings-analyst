from pathlib import Path

from clean_filing import html_to_text

html = Path("data/raw/nvda_10q_2026-07-26.htm").read_bytes()
text = html_to_text(html)

print(f"Characters: {len(text):,}")
print(f"Words: {len(text.split()):,}")

out = Path("data/processed/nvda_10q_2026-07-26.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(text, encoding="utf-8")
print(f"Saved {out}")