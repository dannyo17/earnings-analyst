import re
from pathlib import Path


def parse_metadata(path):
    """Read company, document type and date from a processed file's name."""
    parts = Path(path).stem.split("_")
    ticker = parts[0]
    if parts[1] == "8-K":
        # e.g. MSFT_8-K_EX-99.1_2026-10-28 (an earnings release exhibit)
        doc_type = f"8-K {parts[2]}"
        date = parts[3]  # filing date
    else:
        # e.g. NVDA_10-Q_2026-07-26 (date is the period the report covers)
        doc_type = parts[1]
        date = parts[2]
    return {
        "ticker": ticker,
        "doc_type": doc_type,
        "date": date,
        "source": Path(path).stem,
    }


def split_long_line(line, max_chars):
    """Split an oversized line at sentence ends (or spaces) into pieces under max_chars."""
    if len(line) <= max_chars:
        return [line]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?]) +", line):
        # a single sentence can still be too long: break it at a space
        while len(sentence) > max_chars:
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:cut])
            sentence = sentence[cut:].lstrip()
        if current and len(current) + 1 + len(sentence) > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text, max_chars=1500, min_chars=200):
    """Group whole lines into chunks of roughly max_chars characters."""
    lines = []
    for line in text.split("\n"):
        lines.extend(split_long_line(line, max_chars))

    chunks, current, size = [], [], 0
    for line in lines:
        if size + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))

    # Fold tiny chunks (page numbers, stray headings) into the previous chunk
    merged = []
    for chunk in chunks:
        if merged and len(chunk) < min_chars:
            merged[-1] += "\n" + chunk
        else:
            merged.append(chunk)
    return merged