---
name: warhammer-40k-army-list
description: Build or check Warhammer 40,000 11th Edition army lists with user-supplied local BSData catalogues, Munitorum YAML, and rules PDFs. Use for requested rosters, points-level armies, upgrades, and legality checks.
---

# Warhammer 40,000 army lists

Use the user's installed sources only. If setup is incomplete, direct them to `DATA_SETUP.md` in this project's root. Do not download or refresh data.

Find units, constraints, attachments, and rules with:

```sh
python .agents/skills/warhammer-40k-rules/scripts/search_rules.py --query "<faction, units, detachment, restrictions>" --faction "<faction>" --limit 12
```

Use MFM for points and Detachment Points, not costs embedded in BSData. Match the requested faction, points ceiling, owned models, and theme. If unspecified, use current matched play, no Legends, and no allies. Check categories, copy limits, wargear, attachments, enhancements, transport capacity, and the applicable force rules. Do not present an unverified condition as legal.

Represent a draft using [the roster schema](references/roster-schema.md), then validate:

```sh
python .agents/skills/warhammer-40k-army-list/scripts/validate_roster.py --roster "<draft.json>"
```

Fix errors and report remaining manual checks. Re-add displayed unit costs independently. Format the final roster with faction, detachment, Force Disposition, battle size, attached groups, remaining unit categories, model counts, wargear, points, and one Warlord. State the installed MFM version/date and BSData catalogue revision. Keep strategy comments outside a saved clean roster unless requested.
