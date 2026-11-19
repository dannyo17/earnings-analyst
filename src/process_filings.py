from pathlib import Path

from clean_filing import html_to_text

RAW = Path("data/raw")
PROCESSED = Path("data/processed")

if __name__ == "__main__":
    for raw_path in sorted(RAW.glob("*/*.htm")):
        text = html_to_text(raw_path.read_bytes())
        out = PROCESSED / raw_path.parent.name / (raw_path.stem + ".txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"{out}  {len(text):,} chars")