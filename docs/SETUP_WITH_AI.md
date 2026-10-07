# Local AI setup handoff

This file is for an AI assistant that has access to this folder and can run commands on the user's computer. If the assistant lacks those abilities, explain the limitation and guide the user through [START_HERE.md](START_HERE.md). Do not claim setup succeeded without checking it.

The user acquires game data manually using [DATA_SETUP.md](DATA_SETUP.md). Do not fetch, scrape, upload, commit, or redistribute rules, catalogues, points, extracted text, or search indexes. Work in this project's root. Keep generated files in the ignored `data/` and `.rag-cache/` folders.

## Complete setup

1. Identify a Python 3.10+ command (`python`, `py`, or `python3`). If none exists, give the user the [official Python download page](https://www.python.org/downloads/) and wait for installation.
2. Check `data/core-rules/` for a Core Rules PDF, `data/core-rules/updates/` for a Universal Rules Updates PDF, `data/catalogues/` for BSData JSON, and `data/mfm/` for `meta.yaml` and faction YAML. If files are missing, give the exact destination from `DATA_SETUP.md` and wait for the user to place them. Never substitute bundled or web-fetched game data.
3. Install the local PDF dependency with `<python> -m pip install -r requirements.txt`. If the environment already has a compatible `pypdf`, no install is needed. Explain any install failure plainly.
4. Run `<python> scripts/prepare_rules.py` to extract text from the user's PDFs on their machine.
5. Run `<python> scripts/check_setup.py` and resolve every missing item. Then run `<python> .agents/skills/warhammer-40k-rules/scripts/search_rules.py --status`. This builds the local full-text index. Inspect counts, MFM version/date, and whether the expected PDFs are shown.
6. Run a small query using an installed faction, such as `<python> .agents/skills/warhammer-40k-rules/scripts/search_rules.py --query "Necron Warriors points" --limit 3`. Confirm it returns local filenames and useful text. If Necrons is not installed, choose a unit from a faction the user installed.
7. In Codex, the two skills under `.agents/skills/` should be found from this project. If they are not visible, restart Codex and try an explicit request to use `warhammer-40k-rules`. In another assistant, read the two `SKILL.md` files and use their scripts; only claim native skill installation if that assistant actually supports and detects this layout.
8. Report what worked, the installed source versions/dates, and any remaining manual checks. Offer one example question. Stop after one successful query; there is no need to rebuild the index again.

The index is local SQLite full-text search. It rebuilds automatically after source files change. No vector database, embeddings service, hosted API, or API key is required.
