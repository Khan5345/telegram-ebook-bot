"""
Downloads and prepares ebook PDFs from Project Gutenberg.

- Books with a gutenberg_id are downloaded directly from Gutenberg's cache.
- Existing files are skipped (delete a file to force a fresh download).
- Falls back to a short sample PDF if the download fails.

Run: python bot/create_samples.py
"""

import os
import time
import urllib.request
import urllib.error
from fpdf import FPDF

from catalog import CATALOG

BOOKS_DIR = os.path.join(os.path.dirname(__file__), "books")
os.makedirs(BOOKS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; EbookLibraryBot/1.0; "
        "+https://replit.com)"
    )
}

# Gutenberg PDF cache URL patterns (tried in order)
GUTENBERG_PDF_URLS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}-images.pdf",
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.pdf",
]


# ── Download helpers ─────────────────────────────────────────────────────────

def try_download_pdf(gutenberg_id: int, out_path: str) -> bool:
    """Try to download a PDF from Gutenberg's cache. Returns True on success."""
    for url_tpl in GUTENBERG_PDF_URLS:
        url = url_tpl.format(id=gutenberg_id)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if data[:4] == b"%PDF":
                with open(out_path, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            continue
    return False


def download_gutenberg_text(gutenberg_id: int) -> str:
    """Download plain text from Gutenberg. Returns empty string on failure."""
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace")
        except Exception:
            continue
    return ""


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Gutenberg header and footer from plain text."""
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG",
        "*** START OF THIS PROJECT GUTENBERG",
        "*END*THE SMALL PRINT!",
        "End of the Project Gutenberg",
    ]
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG",
        "*** END OF THIS PROJECT GUTENBERG",
        "End of Project Gutenberg",
        "End of the Project Gutenberg",
    ]

    # Find start
    start_idx = 0
    for marker in start_markers:
        pos = text.find(marker)
        if pos != -1:
            # Skip to end of that line
            start_idx = text.find("\n", pos) + 1
            break

    # Find end
    end_idx = len(text)
    for marker in end_markers:
        pos = text.find(marker, start_idx)
        if pos != -1:
            end_idx = pos
            break

    return text[start_idx:end_idx].strip()


def to_latin1(text: str) -> str:
    """Replace common Unicode characters with Latin-1-safe equivalents."""
    replacements = {
        "\u2014": "--", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00e0": "a", "\u00e2": "a", "\u00e4": "a", "\u00e1": "a",
        "\u00f4": "o", "\u00f6": "o", "\u00f3": "o",
        "\u00fb": "u", "\u00fc": "u", "\u00fa": "u",
        "\u00ee": "i", "\u00ef": "i", "\u00ed": "i",
        "\u00e7": "c", "\u00f1": "n",
        "\u00c9": "E", "\u00c0": "A", "\u00c8": "E",
        "\u00d6": "O", "\u00dc": "U", "\u00d1": "N",
        "\u00ab": '"', "\u00bb": '"',
        "\u2022": "*", "\u00b7": "*",
        "\u00a0": " ", "\u00ad": "-",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ── PDF creation ─────────────────────────────────────────────────────────────

MAX_TEXT_CHARS = 200_000  # ~100 pages worth


def make_pdf_from_text(out_path: str, title: str, author: str, body: str) -> None:
    """Create a well-formatted PDF from plain text using fpdf2."""
    body = to_latin1(body[:MAX_TEXT_CHARS])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)

    # Title page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 26)
    pdf.ln(50)
    pdf.multi_cell(0, 12, to_latin1(title), align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 15)
    pdf.multi_cell(0, 8, f"by {to_latin1(author)}", align="C")
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(0, 6, "Source: Project Gutenberg (www.gutenberg.org)", align="C")

    # Body
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    for para in paragraphs:
        # Treat ALL-CAPS short lines as chapter headings
        if len(para) < 80 and para == para.upper() and len(para) > 3:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 7, para)
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 11)
        else:
            pdf.multi_cell(0, 6, para)
            pdf.ln(3)

    pdf.output(out_path)


def make_fallback_pdf(out_path: str, book: dict) -> None:
    """Create a minimal placeholder PDF when download fails."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.ln(40)
    pdf.multi_cell(0, 10, to_latin1(book["title"]), align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(0, 7, f"by {to_latin1(book['author'])}", align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(
        0, 6,
        "This file could not be downloaded at this time.\n"
        "Please replace it with the full ebook from Project Gutenberg:\n"
        f"  www.gutenberg.org/ebooks/{book.get('gutenberg_id', '')}",
        align="C",
    )
    pdf.output(out_path)


# ── Orchestration ────────────────────────────────────────────────────────────

def process_book(book: dict) -> None:
    filename = book["filename"]
    out_path = os.path.join(BOOKS_DIR, filename)

    if os.path.exists(out_path):
        print(f"  [skip]     {filename}")
        return

    gutenberg_id = book.get("gutenberg_id")
    if not gutenberg_id:
        make_fallback_pdf(out_path, book)
        print(f"  [fallback] {filename}  (no Gutenberg ID)")
        return

    # 1. Try PDF download
    print(f"  [download] {filename}  (PG#{gutenberg_id}) ...", end="", flush=True)
    if try_download_pdf(gutenberg_id, out_path):
        size_kb = os.path.getsize(out_path) // 1024
        print(f"  {size_kb} KB  OK")
        time.sleep(1)  # be polite to Gutenberg
        return

    # 2. Fall back to text → PDF
    print(" (PDF unavailable, trying text...)", end="", flush=True)
    text = download_gutenberg_text(gutenberg_id)
    if text:
        body = strip_gutenberg_boilerplate(text)
        make_pdf_from_text(out_path, book["title"], book["author"], body)
        size_kb = os.path.getsize(out_path) // 1024
        print(f"  {size_kb} KB  OK (from text)")
        time.sleep(1)
        return

    # 3. Placeholder
    make_fallback_pdf(out_path, book)
    print(f"  FAILED — placeholder created")


def main() -> None:
    print(f"Book directory: {BOOKS_DIR}\n")
    for book in CATALOG:
        process_book(book)
    print("\nDone.")


if __name__ == "__main__":
    main()
