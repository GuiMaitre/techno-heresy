#!/usr/bin/env python3
"""Extract text from PDFs the user placed in data/core-rules. No network access."""

from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "core-rules"


def main() -> None:
    pdfs = sorted(RULES.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {RULES}. See DATA_SETUP.md.")
    for pdf in pdfs:
        output = pdf.with_suffix(".txt")
        if output.exists() and output.stat().st_mtime_ns >= pdf.stat().st_mtime_ns:
            print(f"Already processed: {pdf.relative_to(ROOT)}")
            continue
        reader = PdfReader(pdf)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append(f"===== PDF PAGE {page_number:03d} =====\n{page.extract_text() or ''}\n")
        output.write_text("\n".join(pages), encoding="utf-8")
        print(f"Processed {len(reader.pages)} pages: {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
