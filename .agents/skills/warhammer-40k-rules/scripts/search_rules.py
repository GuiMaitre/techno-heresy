#!/usr/bin/env python3
"""Build and query a local FTS index for the Warhammer 40K data folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[4]
CACHE_DIR = PROJECT_ROOT / ".rag-cache"
DB_PATH = CACHE_DIR / "warhammer-40k-rules.sqlite3"

TOKEN_RE = re.compile(r"[\w’']+", re.UNICODE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do",
    "does", "for", "from", "how", "i", "if", "in", "is", "it", "may", "of",
    "after", "on", "or", "that", "the", "then", "this", "to", "what", "when", "where",
    "which", "while", "who", "with", "would", "x", "y",
}
IGNORED_KEYS = {
    "id", "targetId", "typeId", "gameSystemId", "childId", "scopeId", "entryId",
    "publicationId", "page", "xmlns", "battleScribeVersion", "authorContact",
}


@dataclass
class Document:
    title: str
    text: str
    source: str
    kind: str
    faction: str


def find_data_roots() -> tuple[Path, Path]:
    rules_root = PROJECT_ROOT / "data" / "catalogues"
    points_root = PROJECT_ROOT / "data" / "mfm"
    if not list(rules_root.glob("*.json")):
        raise SystemExit(f"No catalogue JSON files in {rules_root}. See DATA_SETUP.md.")
    if not (points_root / "meta.yaml").is_file():
        raise SystemExit(f"No MFM meta.yaml in {points_root}. See DATA_SETUP.md.")
    return rules_root, points_root


def source_files() -> tuple[Path, Path, Path, list[Path]]:
    rules_root, points_root = find_data_roots()
    core_root = PROJECT_ROOT / "data" / "core-rules"
    files = (
        sorted(rules_root.glob("*.json"))
        + sorted(points_root.glob("*.yaml"))
        + sorted(core_root.rglob("*.txt"))
        + sorted(core_root.rglob("*.pdf"))
        + sorted(core_root.rglob("source.json"))
    )
    return rules_root, points_root, core_root, files


def signature(files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        stat = path.stat()
        digest.update(str(path.relative_to(PROJECT_ROOT)).encode("utf-8"))
        digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("ascii"))
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def scalar_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_node(value: Any, prefix: str = "", depth: int = 0) -> list[str]:
    if depth > 9:
        return []
    lines: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in IGNORED_KEYS:
                continue
            child_prefix = f"{prefix}.{key}" if prefix else key
            if isinstance(child, dict) and depth > 0 and child.get("name") and "$text" not in child:
                lines.append(f"{child_prefix}.name: {child['name']}")
                child_kind = child.get("type") or child.get("typeName")
                if child_kind:
                    lines.append(f"{child_prefix}.type: {child_kind}")
            elif isinstance(child, (dict, list)):
                lines.extend(flatten_node(child, child_prefix, depth + 1))
            else:
                text = scalar_text(child).strip()
                if text:
                    lines.append(f"{child_prefix}: {text}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            if isinstance(child, dict) and depth > 0 and child.get("name") and "$text" not in child:
                lines.append(f"{child_prefix}.name: {child['name']}")
                child_kind = child.get("type") or child.get("typeName")
                if child_kind:
                    lines.append(f"{child_prefix}.type: {child_kind}")
            elif isinstance(child, (dict, list)):
                lines.extend(flatten_node(child, child_prefix, depth + 1))
            else:
                text = scalar_text(child).strip()
                if text:
                    lines.append(f"{child_prefix}: {text}")
    return lines


def split_document(doc: Document, max_chars: int = 11000) -> Iterable[Document]:
    if len(doc.text) <= max_chars:
        yield doc
        return
    lines = doc.text.splitlines()
    chunk: list[str] = []
    size = 0
    part = 1
    for line in lines:
        if chunk and size + len(line) + 1 > max_chars:
            yield Document(f"{doc.title} (part {part})", "\n".join(chunk), doc.source, doc.kind, doc.faction)
            part += 1
            chunk = []
            size = 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        yield Document(f"{doc.title} (part {part})", "\n".join(chunk), doc.source, doc.kind, doc.faction)


def json_documents(path: Path) -> Iterable[Document]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    catalogue = data.get("catalogue", {})
    faction = str(catalogue.get("name") or path.stem)
    revision = catalogue.get("revision", "unknown")
    header = f"Catalogue: {faction}\nCatalogue revision: {revision}"

    def walk(value: Any, json_path: str, ancestors: tuple[str, ...]) -> Iterable[Document]:
        if isinstance(value, dict):
            raw_name = value.get("name")
            name = str(raw_name).strip() if raw_name is not None else ""
            next_ancestors = ancestors + ((name,) if name else ())
            is_leaf_characteristic = "$text" in value and set(value).issubset({"name", "$text", "id", "typeId"})
            has_substance = not is_leaf_characteristic and bool(
                "description" in value
                or any(
                    key in value
                    for key in (
                        "profiles", "rules", "characteristics", "selectionEntries",
                        "selectionEntryGroups", "entryLinks", "constraints", "modifiers", "costs",
                    )
                )
            )
            if name and has_substance:
                kind = str(value.get("type") or value.get("typeName") or "named rule entity")
                context = " > ".join(next_ancestors[-6:])
                lines = [header, f"Context: {context}", f"Entity type: {kind}"]
                lines.extend(flatten_node(value))
                text = "\n".join(dict.fromkeys(lines))
                source = f"{rel(path)}#{json_path}"
                yield from split_document(Document(name, text, source, kind, faction))
            for key, child in value.items():
                child_path = f"{json_path}/{key}"
                yield from walk(child, child_path, next_ancestors)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                yield from walk(child, f"{json_path}/{idx}", ancestors)

    yield from walk(data, "$", ())


def parse_yaml_header(lines: list[str]) -> dict[str, str]:
    header: dict[str, str] = {}
    for line in lines:
        if line.startswith(("detachments:", "units:", "notes:", "factions:")):
            break
        match = re.match(r"^([A-Za-z][\w]*):\s*[\"']?(.*?)[\"']?\s*$", line)
        if match:
            header[match.group(1)] = match.group(2)
    return header


def yaml_name(line: str) -> str:
    value = line.split(":", 1)[1].strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value


def yaml_documents(path: Path) -> Iterable[Document]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if path.name == "meta.yaml":
        yield Document("Munitorum Field Manual notes and metadata", text, rel(path), "MFM metadata", "All factions")
        return

    header = parse_yaml_header(lines)
    faction = header.get("name", path.stem.replace("-", " ").title())
    provenance = (
        f"Faction: {faction}\nMFM version: {header.get('version', 'unknown')}\n"
        f"First seen: {header.get('firstSeen', 'unknown')}"
    )
    section = ""
    starts: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        if line == "detachments:":
            section = "detachment"
        elif line == "units:":
            section = "unit"
        elif re.match(r"^  - name:\s*", line) and section:
            starts.append((idx, section, yaml_name(line)))

    for pos, (start, kind, name) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start:end]).rstrip()
        yield from split_document(
            Document(name, f"{provenance}\nEntity type: MFM {kind}\n{body}", f"{rel(path)}#L{start + 1}", f"MFM {kind}", faction)
        )


def clean_extracted_text(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]+", " ", text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()).strip()


def core_rule_documents(path: Path) -> Iterable[Document]:
    raw = path.read_text(encoding="utf-8-sig")
    parts = re.split(r"^===== PDF PAGE (\d{3}) =====\s*$", raw, flags=re.MULTILINE)
    pdf_path = path.with_suffix(".pdf")
    is_update = "updates" in path.relative_to(PROJECT_ROOT).parts
    kind = "official rules update" if is_update else "official core rules"
    provenance = (
        "User-supplied Games Workshop Universal Rules Updates"
        if is_update else "User-supplied Games Workshop Core Rules"
    )
    for idx in range(1, len(parts), 2):
        page = int(parts[idx])
        body = clean_extracted_text(parts[idx + 1])
        if not body:
            continue
        lines = [line for line in body.splitlines() if line]
        title = next((line for line in lines if len(line) <= 100), f"Core Rules page {page}")
        text = f"{provenance}\nPDF page: {page}\n{body}"
        yield Document(
            title,
            text,
            f"{rel(pdf_path)}#page={page}",
            kind,
            "Warhammer 40,000",
        )


def build_index(rules_root: Path, points_root: Path, core_root: Path, files: list[Path], sig: str) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = DB_PATH.with_suffix(".tmp.sqlite3")
    if temp_path.exists():
        temp_path.unlink()
    conn = sqlite3.connect(temp_path)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                kind TEXT NOT NULL,
                faction TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE docs_fts USING fts5(
                title, text, faction,
                content='docs', content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            );
            """
        )
        count = 0
        for path in files:
            if path.parent == rules_root and path.suffix.lower() == ".json":
                docs = json_documents(path)
            elif path.parent == points_root and path.suffix.lower() == ".yaml":
                docs = yaml_documents(path)
            elif core_root in path.parents and path.suffix.lower() == ".txt":
                docs = core_rule_documents(path)
            else:
                continue
            for doc in docs:
                cursor = conn.execute(
                    "INSERT INTO docs(title, text, source, kind, faction) VALUES (?, ?, ?, ?, ?)",
                    (doc.title, doc.text, doc.source, doc.kind, doc.faction),
                )
                conn.execute(
                    "INSERT INTO docs_fts(rowid, title, text, faction) VALUES (?, ?, ?, ?)",
                    (cursor.lastrowid, doc.title, doc.text, doc.faction),
                )
                count += 1
        meta = {
            "signature": sig,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "document_count": str(count),
            "rules_root": rel(rules_root),
            "points_root": rel(points_root),
            "core_root": rel(core_root),
        }
        conn.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", meta.items())
        conn.commit()
    finally:
        conn.close()
    os.replace(temp_path, DB_PATH)
    return count


def read_metadata() -> dict[str, str]:
    if not DB_PATH.exists():
        return {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return dict(conn.execute("SELECT key, value FROM metadata"))
    except sqlite3.DatabaseError:
        return {}


def ensure_index(force: bool = False) -> tuple[dict[str, str], bool]:
    rules_root, points_root, core_root, files = source_files()
    sig = signature(files)
    meta = read_metadata()
    rebuilt = force or meta.get("signature") != sig
    if rebuilt:
        build_index(rules_root, points_root, core_root, files, sig)
        meta = read_metadata()
    return meta, rebuilt


def tokens(text: str) -> list[str]:
    normalized = text.lower().replace("’", "'")
    result = [t.strip("'") for t in TOKEN_RE.findall(normalized)]
    meaningful = [t for t in result if len(t) > 1 and t not in STOPWORDS]
    return list(dict.fromkeys(meaningful or [t for t in result if len(t) > 1]))


def fts_query(query: str) -> str:
    terms = tokens(query)
    if not terms:
        raise SystemExit("The query needs at least one searchable word.")
    safe = [term.replace('"', '""') for term in terms]
    return " OR ".join(f'"{term}"*' for term in safe)


def search(query: str, faction: str | None, limit: int) -> list[dict[str, Any]]:
    match = fts_query(query)
    params: list[Any] = [match]
    where = "docs_fts MATCH ?"
    if faction:
        where += " AND lower(d.faction) LIKE ?"
        params.append(f"%{faction.lower()}%")
    params.append(max(limit * 15, 80))
    sql = f"""
        SELECT d.id, d.title, d.text, d.source, d.kind, d.faction,
               bm25(docs_fts, 8.0, 1.0, 4.0) AS rank
        FROM docs_fts
        JOIN docs d ON d.id = docs_fts.rowid
        WHERE {where}
        ORDER BY rank
        LIMIT ?
    """
    query_tokens = tokens(query)
    query_norm = " ".join(query_tokens)
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(sql, params).fetchall()

    ranked: list[tuple[float, tuple[Any, ...]]] = []
    for row in rows:
        _, title, text, _, kind, row_faction, bm25_rank = row
        title_norm = title.lower().replace("’", "'")
        text_norm = text.lower().replace("’", "'")
        faction_norm = row_faction.lower().replace("’", "'")
        coverage = sum(1 for token in query_tokens if token in text_norm or token in title_norm)
        title_hits = sum(1 for token in query_tokens if token in title_norm)
        score = coverage * 5 + title_hits * 10 + max(0.0, -float(bm25_rank))
        if title_norm in query_tokens:
            score += 25
        if query_norm and query_norm in " ".join(tokens(title_norm)):
            score += 35
        if row_faction == "Warhammer 40,000":
            score += 12
        if kind == "official rules update":
            score += 60
        if faction and faction.lower() in faction_norm:
            score += 12
        if kind.startswith("MFM") and any(word in query.lower() for word in ("point", "cost", "dp", "price")):
            score += 12
        ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for score, row in ranked:
        _, title, text, source, kind, row_faction, _ = row
        key = (title.replace(" (part 1)", ""), source.split("#", 1)[0])
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {"title": title, "kind": kind, "faction": row_faction, "source": source, "score": round(score, 3), "text": text}
        )
        if len(results) >= limit:
            break
    return results


def mfm_metadata(points_root: Path) -> dict[str, str]:
    lines = (points_root / "meta.yaml").read_text(encoding="utf-8-sig").splitlines()
    return parse_yaml_header(lines)


def print_status(meta: dict[str, str], rebuilt: bool) -> None:
    rules_root, points_root, core_root, files = source_files()
    mfm = mfm_metadata(points_root)
    json_files = sum(1 for f in rules_root.glob("*.json"))
    yaml_files = sum(1 for f in points_root.glob("*.yaml"))
    core_pdf = next(iter(sorted(core_root.glob("*.pdf"))), None)
    update_pdfs = sorted((core_root / "updates").glob("*.pdf"))
    print(f"Project: {PROJECT_ROOT}")
    print(f"Rules source: {rel(rules_root)} ({json_files} JSON files)")
    print(f"Points source: {rel(points_root)} ({yaml_files} YAML files)")
    print(f"Official core rules: {rel(core_pdf) if core_pdf else 'not installed'}")
    print(f"Universal rules updates: {len(update_pdfs)} file(s); check the PDF for its effective date")
    print(f"MFM version: {mfm.get('version', 'unknown')}")
    print(f"MFM lastUpdated: {mfm.get('lastUpdated', 'unknown')}")
    print(f"Indexed documents: {meta.get('document_count', 'unknown')}")
    print(f"Index built (UTC): {meta.get('built_at', 'unknown')}")
    print(f"Index rebuilt this run: {'yes' if rebuilt else 'no'}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", "-q", help="Rules or points question to retrieve evidence for")
    parser.add_argument("--faction", help="Optional faction-name filter")
    parser.add_argument("--limit", type=int, default=8, help="Maximum results (default: 8)")
    parser.add_argument("--max-chars", type=int, default=5000, help="Text characters per printed result")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--status", action="store_true", help="Show source and index freshness")
    parser.add_argument("--rebuild", action="store_true", help="Force a clean index rebuild")
    args = parser.parse_args()
    if not args.status and not args.query:
        parser.error("provide --query or --status")
    if args.limit < 1 or args.limit > 50:
        parser.error("--limit must be between 1 and 50")

    meta, rebuilt = ensure_index(args.rebuild)
    if args.status:
        print_status(meta, rebuilt)
        if not args.query:
            return 0

    results = search(args.query, args.faction, args.limit)
    if args.json:
        payload = {"query": args.query, "faction": args.faction, "results": results, "metadata": meta}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Query: {args.query}")
    if args.faction:
        print(f"Faction filter: {args.faction}")
    print(f"Results: {len(results)}\n")
    for idx, result in enumerate(results, 1):
        print(f"[{idx}] {result['title']} | {result['kind']} | {result['faction']}")
        print(f"Source: {result['source']}")
        print(result["text"][: args.max_chars].rstrip())
        if len(result["text"]) > args.max_chars:
            print("[truncated]")
        print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
