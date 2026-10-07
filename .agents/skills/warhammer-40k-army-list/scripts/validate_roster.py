#!/usr/bin/env python3
"""Validate a draft 11e roster against the local MFM dataset."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


def project_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[4]


ROOT = project_root()


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("‑", "-")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def scalar(lines: list[str], key: str) -> str | None:
    rx = re.compile(rf"^{re.escape(key)}:\s*[\"']?(.*?)[\"']?\s*$")
    for line in lines:
        match = rx.match(line)
        if match:
            return match.group(1)
    return None


def flow_value(line: str, key: str) -> str | None:
    pattern = rf"(?:\{{|,)\s*{re.escape(key)}:\s*(.*?)(?=,\s*[A-Za-z][A-Za-z0-9_]*:|\s*\}})"
    match = re.search(pattern, line)
    return match.group(1).strip().strip("\"'") if match else None


def named_blocks(lines: list[str]) -> list[list[str]]:
    starts = [i for i, line in enumerate(lines) if re.match(r"^  - name:\s*", line)]
    return [lines[start : starts[pos + 1] if pos + 1 < len(starts) else len(lines)] for pos, start in enumerate(starts)]


def parse_range(text: str) -> tuple[int, int | None]:
    match = re.fullmatch(r"\[(\d+),\s*(\d*)\)", text) or re.fullmatch(r"\[(\d+),\s*(\d+)\]", text)
    if not match:
        raise ValueError(f"Unsupported requisition range: {text}")
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


def parse_detachment(block: list[str]) -> dict[str, Any]:
    item: dict[str, Any] = {"name": block[0].split(":", 1)[1].strip(), "objectives": [], "enhancements": []}
    in_objectives = False
    in_enhancements = False
    for line in block[1:]:
        stripped = line.strip()
        if line.startswith("    dp:"):
            item["dp"] = int(stripped.split(":", 1)[1])
        elif line.startswith("    unique:"):
            item["unique"] = stripped.split(":", 1)[1].strip()
        elif line.startswith("    objectives:"):
            in_objectives, in_enhancements = True, False
        elif line.startswith("    enhancements:"):
            in_objectives, in_enhancements = False, True
        elif re.match(r"^    [A-Za-z].*:", line):
            in_objectives = in_enhancements = False
        elif in_objectives and line.startswith("      - "):
            item["objectives"].append(stripped[2:].strip())
        elif in_enhancements and line.startswith("      - {"):
            name, points = flow_value(line, "name"), flow_value(line, "points")
            if name and points:
                item["enhancements"].append({"name": name, "points": int(points)})
    return item


def parse_unit(block: list[str]) -> dict[str, Any]:
    unit: dict[str, Any] = {
        "name": block[0].split(":", 1)[1].strip(),
        "pricing": [], "leaderTo": [], "supportTo": [], "wargear": [],
    }
    current_tier: dict[str, Any] | None = None
    list_key: str | None = None
    for line in block[1:]:
        stripped = line.strip()
        if line.startswith("    legends:"):
            unit["legends"] = stripped.endswith("true")
        elif line.startswith("      - range:"):
            range_text = stripped.split(":", 1)[1].strip().strip("\"'")
            current_tier = {"range": parse_range(range_text), "costs": []}
            unit["pricing"].append(current_tier)
            list_key = None
        elif line.startswith("          - {") and current_tier is not None:
            models, points = flow_value(line, "models"), flow_value(line, "points")
            if models and points:
                cost = {"models": int(models), "points": int(points)}
                desc = flow_value(line, "desc")
                if desc:
                    cost["desc"] = desc
                current_tier["costs"].append(cost)
        elif line.startswith("    leaderTo:"):
            list_key = "leaderTo"
        elif line.startswith("    supportTo:"):
            list_key = "supportTo"
        elif line.startswith("    wargear:"):
            list_key = "wargear"
        elif line.startswith("      - {") and list_key == "wargear":
            name, points = flow_value(line, "item"), flow_value(line, "points")
            if name and points:
                unit["wargear"].append({"item": name, "points": int(points)})
        elif line.startswith("      - ") and list_key in {"leaderTo", "supportTo"}:
            unit[list_key].append(stripped[2:].strip())
        elif re.match(r"^    [A-Za-z].*:", line):
            list_key = None
    return unit


def load_faction(requested: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data_dir = ROOT / "data" / "mfm"
    if not (data_dir / "meta.yaml").is_file():
        raise SystemExit(f"No MFM meta.yaml in {data_dir}. See DATA_SETUP.md.")
    for path in data_dir.glob("*.yaml"):
        if path.name == "meta.yaml":
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        name = scalar(lines, "name")
        slug = scalar(lines, "slug")
        if norm(requested) not in {norm(name), norm(slug), norm(path.stem)}:
            continue
        units_at = lines.index("units:")
        detach_at = lines.index("detachments:") if "detachments:" in lines else units_at
        faction = {
            "name": name,
            "slug": slug,
            "version": scalar(lines, "version"),
            "firstSeen": scalar(lines, "firstSeen"),
            "detachments": [parse_detachment(b) for b in named_blocks(lines[detach_at + 1 : units_at])],
            "units": [parse_unit(b) for b in named_blocks(lines[units_at + 1 :])],
            "path": path.relative_to(ROOT).as_posix(),
        }
        meta_lines = (data_dir / "meta.yaml").read_text(encoding="utf-8-sig").splitlines()
        meta = {"version": scalar(meta_lines, "version"), "lastUpdated": scalar(meta_lines, "lastUpdated")}
        return faction, meta
    raise SystemExit(f"No MFM faction matched {requested!r}.")


def lookup(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    wanted = norm(name)
    return next((item for item in items if norm(item["name"]) == wanted), None)


def select_cost(unit: dict[str, Any], instance: int, models: int, desc: str | None) -> tuple[dict[str, Any] | None, str | None]:
    tier = next((t for t in unit["pricing"] if instance >= t["range"][0] and (t["range"][1] is None or instance <= t["range"][1])), None)
    if not tier:
        return None, f"No pricing tier covers copy {instance}."
    choices = tier["costs"]
    if desc:
        choices = [c for c in choices if norm(c.get("desc", "")) == norm(desc)]
        if not choices:
            return None, f"No pricing option has cost_desc {desc!r}."
    eligible = sorted((c for c in choices if c["models"] >= models), key=lambda c: c["models"])
    if not eligible:
        return None, f"No published starting-strength option accommodates {models} model(s)."
    chosen = eligible[0]
    same_size = [c for c in choices if c["models"] == chosen["models"]]
    if len(same_size) > 1 and not desc:
        return None, f"Multiple {chosen['models']}-model costs exist; provide cost_desc."
    warning = None
    if models not in {c["models"] for c in choices}:
        warning = f"{models} models are charged at the published {chosen['models']}-model cost."
    return chosen, warning


def validate(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    faction, meta = load_faction(spec.get("faction", ""))
    detachments: list[dict[str, Any]] = []
    for name in spec.get("detachments", []):
        found = lookup(faction["detachments"], name)
        if found:
            detachments.append(found)
        else:
            errors.append(f"Unknown detachment: {name}.")

    battle_size = norm(spec.get("battle_size", ""))
    size_rules = {"incursion": (1000, 2, 2), "strike force": (2000, 3, 4), "onslaught": (3000, 4, 4)}
    if battle_size not in size_rules:
        errors.append("battle_size must be Incursion, Strike Force, or Onslaught.")
        standard_limit, dp_limit, enhancement_limit = (0, 0, 0)
    else:
        standard_limit, dp_limit, enhancement_limit = size_rules[battle_size]
    if battle_size == "incursion" and any(d.get("dp") == 3 for d in detachments):
        dp_limit = 3
    points_limit = int(spec.get("points_limit", standard_limit) or 0)
    dp_total = sum(d.get("dp", 0) for d in detachments)
    if dp_total > dp_limit:
        errors.append(f"Detachments cost {dp_total} DP, above the {dp_limit} DP {spec.get('battle_size')} limit.")
    unique_tags = [norm(d["unique"]) for d in detachments if d.get("unique")]
    for tag, count in Counter(unique_tags).items():
        if count > 1:
            errors.append(f"Multiple detachments use the same unique tag: {tag}.")
    disposition = norm(spec.get("force_disposition", ""))
    offered = {norm(x) for d in detachments for x in d.get("objectives", [])}
    if disposition and disposition not in offered:
        errors.append(f"Force Disposition {spec.get('force_disposition')!r} is not granted by a selected detachment.")

    expanded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in spec.get("units", []):
        copies = int(raw.get("copies", 1))
        if copies < 1:
            errors.append(f"{raw.get('name', 'Unnamed unit')}: copies must be at least 1.")
            continue
        for copy in range(copies):
            item = dict(raw)
            base_id = str(raw.get("id", "")).strip()
            item["id"] = base_id if copies == 1 else f"{base_id}-{copy + 1}"
            if not item["id"]:
                errors.append(f"{raw.get('name', 'Unnamed unit')}: every unit needs an id.")
            elif item["id"] in seen_ids:
                errors.append(f"Duplicate unit id: {item['id']}.")
            seen_ids.add(item["id"])
            expanded.append(item)

    occurrence: Counter[str] = Counter()
    breakdown: list[dict[str, Any]] = []
    total = 0
    unit_by_id: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for selected in expanded:
        name = str(selected.get("name", ""))
        unit = lookup(faction["units"], name)
        if not unit:
            errors.append(f"Unknown unit: {name}.")
            continue
        if unit.get("legends") and not spec.get("allow_legends", False):
            errors.append(f"{unit['name']} is marked Legends; set allow_legends only if explicitly intended.")
        key = norm(unit["name"])
        occurrence[key] += 1
        models = int(selected.get("models", 0))
        cost, warning = select_cost(unit, occurrence[key], models, selected.get("cost_desc"))
        if not cost:
            errors.append(f"{unit['name']} ({selected.get('id')}): {warning}")
            continue
        if warning:
            warnings.append(f"{unit['name']} ({selected.get('id')}): {warning}")
        unit_points = cost["points"]
        paid_items: list[dict[str, Any]] = []
        for raw_gear in selected.get("paid_wargear", []):
            gear_name = raw_gear if isinstance(raw_gear, str) else raw_gear.get("item", "")
            quantity = 1 if isinstance(raw_gear, str) else int(raw_gear.get("quantity", 1))
            gear = next((g for g in unit["wargear"] if norm(g["item"]) == norm(gear_name)), None)
            if not gear:
                errors.append(f"{unit['name']}: {gear_name!r} is not listed as paid MFM wargear.")
                continue
            unit_points += gear["points"] * quantity
            paid_items.append({"item": gear["item"], "quantity": quantity, "points": gear["points"] * quantity})
        total += unit_points
        breakdown.append({"id": selected.get("id"), "name": unit["name"], "models": models, "points": unit_points, "paid_wargear": paid_items})
        unit_by_id[str(selected.get("id"))] = (selected, unit)

    enhancements: list[dict[str, Any]] = []
    available_enhancements = [e for d in detachments for e in d.get("enhancements", [])]
    if len(spec.get("enhancements", [])) > enhancement_limit:
        errors.append(f"{len(spec.get('enhancements', []))} enhancements exceed the {enhancement_limit} allowed at {spec.get('battle_size')}.")
    for chosen in spec.get("enhancements", []):
        name = chosen if isinstance(chosen, str) else chosen.get("name", "")
        enhancement = lookup(available_enhancements, name)
        if not enhancement:
            errors.append(f"Enhancement {name!r} is not available from the selected detachments.")
            continue
        bearer = None if isinstance(chosen, str) else chosen.get("bearer")
        if bearer and bearer not in unit_by_id:
            errors.append(f"Enhancement {enhancement['name']} names unknown bearer id {bearer!r}.")
        total += enhancement["points"]
        enhancements.append({"name": enhancement["name"], "points": enhancement["points"], "bearer": bearer})

    for attached in spec.get("attachments", []):
        actor_id, bodyguard_id = str(attached.get("actor", "")), str(attached.get("bodyguard", ""))
        if actor_id not in unit_by_id or bodyguard_id not in unit_by_id:
            errors.append(f"Attachment references unknown id(s): {actor_id!r} -> {bodyguard_id!r}.")
            continue
        actor = unit_by_id[actor_id][1]
        bodyguard = unit_by_id[bodyguard_id][1]
        kind = norm(attached.get("type", "leader"))
        field = "supportTo" if kind == "support" else "leaderTo"
        if norm(bodyguard["name"]) not in {norm(x) for x in actor[field]}:
            errors.append(f"{actor['name']} cannot attach to {bodyguard['name']} as {kind.title()} in the MFM data.")

    warlords = [unit for unit in expanded if unit.get("warlord") is True]
    if len(warlords) != 1:
        errors.append(f"Roster must mark exactly one Warlord; found {len(warlords)}.")
    if total > points_limit:
        errors.append(f"Roster costs {total} points, {total - points_limit} above the {points_limit}-point limit.")

    warnings.extend([
        "Verify BSData categories and per-datasheet copy limits.",
        "Verify faction/allied eligibility and every model-level wargear quantity.",
        "Verify enhancement bearer restrictions and transport capacity where applicable.",
    ])
    return {
        "valid_mfm": not errors,
        "faction": faction["name"],
        "mfm_version": meta["version"],
        "mfm_last_updated": meta["lastUpdated"],
        "points": total,
        "points_limit": points_limit,
        "points_remaining": points_limit - total,
        "detachment_points": dp_total,
        "detachment_points_limit": dp_limit,
        "breakdown": breakdown,
        "enhancements": enhancements,
        "errors": errors,
        "warnings": warnings,
        "source": faction["path"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", required=True, type=Path, help="Path to the draft roster JSON.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()
    try:
        spec = json.loads(args.roster.read_text(encoding="utf-8-sig"))
        result = validate(spec)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        state = "PASS" if result["valid_mfm"] else "FAIL"
        print(f"{state}: {result['faction']} - {result['points']}/{result['points_limit']} points; {result['detachment_points']}/{result['detachment_points_limit']} DP")
        print(f"MFM v{result['mfm_version']} (updated {result['mfm_last_updated']})")
        for item in result["breakdown"]:
            print(f"  {item['name']} [{item['id']}]: {item['points']} points")
        for item in result["enhancements"]:
            print(f"  {item['name']} (Enhancement): {item['points']} points")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
    return 0 if result["valid_mfm"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
