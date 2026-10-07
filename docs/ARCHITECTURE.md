# Architecture

Techno-Heresy is a local reference workflow packaged as two agent skills. Users provide the source files; the project provides extraction, search, and roster checks. There is no application server or remote database.

## Components

| Component | Responsibility | Reads | Writes |
| --- | --- | --- | --- |
| `scripts/prepare_rules.py` | Extract text with PDF page markers | User-supplied PDFs in `data/core-rules/` | Text files beside those PDFs |
| `warhammer-40k-rules` skill | Retrieve relevant passages and explain rules interactions | Core-rule text, BSData JSON, Munitorum YAML | Local SQLite index in `.rag-cache/` |
| `warhammer-40k-army-list` skill | Draft a roster and check its points and attachments | The same local sources | A roster only when the user asks to save one |
| `scripts/check_setup.py` | Report missing prerequisites and files | Python environment and local file names | Nothing |

The rules retriever uses SQLite FTS5. It indexes local source text on first use and rebuilds when those files change. It returns source paths and PDF page numbers so answers can be checked against the user's files. This is lexical search, not an embedding or vector service.

## Data boundary

`data/`, `.rag-cache/`, and `list/` are ignored by Git. Project scripts do not download, scrape, or upload game data. Installing the `pypdf` dependency through Python's package manager does require a package download unless it is already installed. A cloud AI assistant may receive excerpts that it reads from the local search output; that boundary depends on the assistant the user chooses.

## Source precedence and validation

Official Universal Rules Updates take precedence over conflicting Core Rules text. BSData catalogues provide community-maintained unit and faction detail. The Munitorum YAML export supplies point costs and Detachment Points; costs embedded in BSData JSON are not used for those calculations.

The roster validator checks deterministic Munitorum constraints, costs, and attachment links. It does not prove all game legality. Model-level wargear, copy limits, faction eligibility, transport capacity, and disputed interactions still need manual review against the installed sources. The skills report those limits instead of claiming tournament certification.

## Portability

Codex discovers skills from `.agents/skills/` when this folder is open as a local project. Other assistants can read the same `SKILL.md` files and run the Python tools if they have local file and command access. The tools resolve paths from their own project folder, so the folder can be moved without editing configuration.
