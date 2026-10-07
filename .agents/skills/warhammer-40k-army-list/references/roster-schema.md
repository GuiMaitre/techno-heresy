# Validator roster schema

Save a temporary UTF-8 JSON file with this shape. `id` values only need to be unique inside the roster.

```json
{
  "name": "Example list",
  "faction": "Death Guard",
  "battle_size": "Strike Force",
  "points_limit": 2000,
  "force_disposition": "DISRUPTION",
  "detachments": ["Flyblown Host", "Tallyband Summoners"],
  "units": [
    {"id": "loc", "name": "Lord of Contagion", "models": 1, "role": "CHARACTERS", "warlord": true, "paid_wargear": []},
    {"id": "blightlords", "name": "Blightlord Terminators", "models": 10, "role": "OTHER DATASHEETS"}
  ],
  "attachments": [
    {"actor": "loc", "bodyguard": "blightlords", "type": "leader"}
  ],
  "enhancements": [
    {"name": "Entropic Knell", "bearer": "loc"}
  ]
}
```

## Fields

- `battle_size`: `Incursion`, `Strike Force`, or `Onslaught`.
- `points_limit`: may override the standard size ceiling, but DP and enhancement limits still follow `battle_size`.
- `units`: write one object per unit selection. `copies` can expand identical selections but separate objects are clearer when loadouts or attachments differ.
- `models`: actual starting strength. When MFM publishes only lower and upper sizes, an intermediate size is charged at the next published size.
- `cost_desc`: required only when MFM has two costs with the same model count but different descriptions.
- `paid_wargear`: array of strings, or objects such as `{"item": "Ectoplasma cannon", "quantity": 2}`. Include only wargear with an MFM points surcharge.
- `role`: display grouping. It does not prove that a datasheet has that category; verify categories in BSData.
- `attachments.type`: `leader` or `support`; `actor` and `bodyguard` refer to unit ids.
- `enhancements`: enhancement names must belong to a selected detachment. Add `bearer` for traceability; verify bearer restrictions in BSData.

The validator reports deterministic MFM checks. Always complete the manual BSData checks listed by the skill.
