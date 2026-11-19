import warnings

from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


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

    # Replace each table with row-per-line text so rows stay intact
    for table in soup.find_all("table"):
        table.replace_with(NavigableString("\n" + table_to_text(table) + "\n"))

    return soup.get_text(separator="\n", strip=True)