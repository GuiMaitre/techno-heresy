#!/usr/bin/env python3
"""Check local prerequisites and user-supplied data without network access."""

from importlib.util import find_spec
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def check(label: str, passed: bool, detail: str) -> bool:
    print(f"{'OK' if passed else 'MISSING'}  {label}: {detail}")
    return passed


def main() -> int:
    print("Techno-Heresy local setup check\n")
    results = []
    results.append(check("Python", sys.version_info >= (3, 10), sys.version.split()[0]))
    has_pypdf = find_spec("pypdf") is not None
    results.append(check(
        "PDF reader", has_pypdf,
        "pypdf installed" if has_pypdf else "run: python -m pip install -r requirements.txt",
    ))

    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE VIRTUAL TABLE test USING fts5(text)")
        has_fts = True
    except sqlite3.OperationalError:
        has_fts = False
    results.append(check("Local search", has_fts, "SQLite FTS5 available" if has_fts else "Python SQLite lacks FTS5"))

    core = list((DATA / "core-rules").glob("*.pdf"))
    updates = list((DATA / "core-rules" / "updates").glob("*.pdf"))
    catalogues = list((DATA / "catalogues").glob("*.json"))
    faction_yaml = [path for path in (DATA / "mfm").glob("*.yaml") if path.name != "meta.yaml"]
    meta = DATA / "mfm" / "meta.yaml"

    results.append(check("Core Rules PDF", bool(core), "data/core-rules/*.pdf"))
    results.append(check("Rules Updates PDF", bool(updates), "data/core-rules/updates/*.pdf"))
    results.append(check("BSData catalogues", bool(catalogues), f"{len(catalogues)} JSON file(s) in data/catalogues/"))
    results.append(check("Munitorum metadata", meta.is_file(), "data/mfm/meta.yaml"))
    results.append(check("Munitorum factions", bool(faction_yaml), f"{len(faction_yaml)} YAML file(s) in data/mfm/"))

    pdfs = core + updates
    extracted = all(
        pdf.with_suffix(".txt").is_file()
        and pdf.with_suffix(".txt").stat().st_mtime_ns >= pdf.stat().st_mtime_ns
        for pdf in pdfs
    )
    results.append(check(
        "Extracted PDF text", bool(pdfs) and extracted,
        "PDF text is ready" if pdfs and extracted else "run: python scripts/prepare_rules.py",
    ))

    print("\nReady to search." if all(results) else "\nFinish the missing items using DATA_SETUP.md, then run this check again.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
