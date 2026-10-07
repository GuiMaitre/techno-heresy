---
name: warhammer-40k-rules
description: Answer Warhammer 40,000 11th Edition rules and points questions using user-supplied local rules PDFs, BSData catalogues, and Munitorum YAML. Use for rules interactions, unit rules, detachments, wargear, and points; not lore or painting.
---

# Warhammer 40,000 rules

Use only the local files that the user has installed. If setup is incomplete, direct them to `DATA_SETUP.md` in this project's root. The skill does not download or refresh data.

From the project root, retrieve evidence with:

```sh
python .agents/skills/warhammer-40k-rules/scripts/search_rules.py --query "<question and exact names>" --limit 8
```

Use `--faction "<name>"` to narrow noisy results, and `--status` to show installed sources. Search separately for each rule or unit in a disputed interaction.

Apply official updates over conflicting core text, use BSData for catalogue and unit detail, and use Munitorum YAML for current points. BSData and the YAML export are community maintained; compare uncertain or tournament-sensitive conclusions with the official sources. Never infer that installed data is current merely because the index rebuilt. Cite local filenames, PDF pages, and the MFM `lastUpdated` value when relevant. If the installed sources cannot establish an answer, state what is missing.
