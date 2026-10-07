# Get and place your own data

New to installing software? Follow [START_HERE.md](START_HERE.md) first, then return to this page for the download links and folder locations.

This project does not include rules, points, catalogues, or a downloader. Download the sources yourself, then place them in the folders below. `data/`, extracted text, saved armies, and the search index are ignored by Git.

## 1. Official rules PDFs

Open the [Warhammer 40,000 downloads page](https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/) and download the current **Core Rules** and **Universal Rules Updates** PDFs. The links and filenames can change, so use the page rather than an old direct PDF link.

Put the files here (the filenames are examples):

```text
data/
  core-rules/
    core-rules.pdf
    updates/
      universal-rules-updates.pdf
```

On your own computer, install Python 3.10 or newer, then run from this project's root. On macOS/Linux, replace `python` with `python3` if needed; on Windows, use `py` if `python` is not recognized:

```sh
python -m pip install -r requirements.txt
python scripts/prepare_rules.py
```

`prepare_rules.py` reads only those local PDFs and writes `.txt` files beside them with PDF page markers. It makes no network requests. Replace outdated PDFs and run it again after official updates. Check each PDF's version and effective date yourself.

## 2. Community catalogue JSON

Open [BSData's Warhammer 40,000 11th Edition repository](https://github.com/BSData/wh40k-11e). Use GitHub's **Code → Download ZIP**. Unzip it on your computer, then copy the top-level `*.json` files, including `Warhammer 40,000.json` and any faction/library catalogues you need, into:

```text
data/catalogues/
```

Copy the JSON files directly into that folder, without the ZIP's enclosing directory. The catalogue is community maintained and may differ from current official rules. Keep a note of the revision/date you downloaded.

## 3. Community Munitorum YAML

The [official Munitorum Field Manual](https://mfm.warhammer-community.com/en) is the reference to check for current points. For machine-readable local files, open [BSData's MFM repository](https://github.com/BSData/wh40k-11e-mfm), use **Code → Download ZIP**, and unzip it on your computer. Copy the contents of its `data/` folder, including `meta.yaml` and the faction `.yaml` files you need, into:

```text
data/mfm/
```

Copy the YAML files directly into `data/mfm/`, without the ZIP's enclosing directory. Check `meta.yaml` for its version and `lastUpdated` date, and compare important costs with the official Munitorum. The community export can lag or contain errors.

## 4. Check your setup

Your local files should now resemble:

```text
data/
  core-rules/
    core-rules.pdf
    core-rules.txt
    updates/
      universal-rules-updates.pdf
      universal-rules-updates.txt
  catalogues/
    Warhammer 40,000.json
    ... faction and library JSON files
  mfm/
    meta.yaml
    ... faction YAML files
```

Run:

```sh
python scripts/check_setup.py
python .agents/skills/warhammer-40k-rules/scripts/search_rules.py --status
python .agents/skills/warhammer-40k-rules/scripts/search_rules.py --query "Necron Warriors points" --limit 3
```

The setup check names any missing item. The search index is built locally on first use. The army-list skill also uses `data/mfm/` for validation. To update, replace your own source files, process any new PDFs, and run a search again; the index detects changed files.

## Data and privacy

Your downloaded source files and armies stay in this folder unless you choose to share them. Do not add `data/`, `.rag-cache/`, or `list/` to a public repository or release archive. A cloud AI platform may receive excerpts returned by the local search tool; check that platform's data settings if privacy matters. Downloading data for personal use does not transfer ownership of Games Workshop's or BSData's intellectual property. Review the applicable [Warhammer Community terms](https://www.warhammer-community.com/en-gb/terms-of-use/) and BSData repository terms yourself.
