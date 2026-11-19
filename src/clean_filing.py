import re
import warnings

from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BLOCK_TAGS = ["p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"]
BULLETS = {"•", "●", "▪", "◦"}


def table_to_text(table):
    """Turn an HTML table into one line per row, with cells joined by ' | '."""
    lines = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        merged = []
        for cell in cells:
            if not cell or cell == "$":
                continue
            if cell in (")", "%", ")%") and merged:
                merged[-1] += cell
                continue
            merged.append(cell)
        if merged:
            lines.append(" | ".join(merged))
    return "\n".join(lines)


def html_to_text(html_bytes):
    """Convert an SEC filing's HTML into clean plain text."""
    soup = BeautifulSoup(html_bytes, "lxml")

    # Remove the hidden machine-readable XBRL header
    for tag in soup.find_all("ix:header"):
        tag.decompose()

    # Collapse whitespace inside text so source-file line wraps don't split sentences
    for node in soup.find_all(string=True):
        if type(node) is NavigableString:
            node.replace_with(re.sub(r"\s+", " ", str(node)))

    # Replace each table with row-per-line text so rows stay intact
    for table in soup.find_all("table"):
        table.replace_with(NavigableString("\n" + table_to_text(table) + "\n"))

    # Line breaks only at block-level elements; links and bold stay in the sentence
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text().replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    # Attach lone bullet characters to the text that follows them
    merged = []
    for line in lines:
        if merged and merged[-1] in BULLETS:
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)

    # Drop the EDGAR header lines that sit above "Exhibit 99.x"
    for i, line in enumerate(merged[:10]):
        if re.fullmatch(r"Exhibit \d+(\.\d+)?", line):
            merged = merged[i + 1:]
            break

    return "\n".join(merged)