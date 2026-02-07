#!/usr/bin/env python3
"""Apply editorial enrichments to a weekly plan JSON file.

Reads plan_data.json and an edits JSON file, merges the editorial changes
into the plan data, and writes the updated JSON. Optionally generates an
editorial report summarizing all changes.

Usage:
    python edit_plan.py plan_data.json --edits edits.json
    python edit_plan.py plan_data.json --edits edits.json -o enriched_plan.json
    python edit_plan.py plan_data.json --edits edits.json --report editorial-report.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


# Fields the editor is allowed to modify per day
EDITABLE_DAY_FIELDS = {
    "day_intro",
    "dinner_description",
    "dinner_notes",
    "album_description",
    "album_pairing_rationale",
    "activity",
    "activity_notes",
}

# Top-level fields the editor is allowed to modify
EDITABLE_TOP_FIELDS = {
    "highlight",
    "nutrition_summary",
}


def apply_edits(data, edits):
    """Merge editorial edits into plan data. Returns a changelog."""
    changelog = []

    # Top-level field edits
    for field in EDITABLE_TOP_FIELDS:
        if field in edits and edits[field]:
            old = data.get(field, "")
            data[field] = edits[field]
            changelog.append({
                "section": "Top-level",
                "field": field,
                "old": old[:80] + "..." if len(old) > 80 else old,
                "new": edits[field][:80] + "..." if len(edits[field]) > 80 else edits[field],
                "action": "replaced" if old else "added",
            })

    # Notes additions (append, don't replace)
    if edits.get("notes_additions"):
        existing = data.get("notes", [])
        for note in edits["notes_additions"]:
            if note not in existing:
                existing.append(note)
                changelog.append({
                    "section": "Notes",
                    "field": "notes",
                    "old": "",
                    "new": note[:80] + "..." if len(note) > 80 else note,
                    "action": "appended",
                })
        data["notes"] = existing

    # Per-day edits
    days = data.get("days", [])
    for day_edit in edits.get("day_edits", []):
        idx = day_edit.get("day_index")
        if idx is None or idx < 0 or idx >= len(days):
            print(f"WARNING: day_index {idx} out of range (0-{len(days)-1}), skipping",
                  file=sys.stderr)
            continue

        day = days[idx]
        day_name = day.get("long_name", day.get("name", f"Day {idx}"))

        for field in EDITABLE_DAY_FIELDS:
            if field in day_edit and day_edit[field]:
                old = day.get(field, "")
                day[field] = day_edit[field]
                changelog.append({
                    "section": day_name,
                    "field": field,
                    "old": old[:60] + "..." if len(str(old)) > 60 else str(old),
                    "new": day_edit[field][:60] + "..." if len(day_edit[field]) > 60 else day_edit[field],
                    "action": "replaced" if old else "added",
                })

    return changelog


def render_report(changelog, data, template_dir, output_path):
    """Render the editorial report from the changelog."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("editorial_report.md.j2")

    report_data = {
        "week_range": data.get("week_range", "Unknown"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "changelog": changelog,
        "total_changes": len(changelog),
        "sections_touched": len(set(c["section"] for c in changelog)),
    }

    content = template.render(report_data)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Editorial report written to {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Apply editorial enrichments to a weekly plan JSON"
    )
    parser.add_argument(
        "input",
        help="Path to the plan_data.json file",
    )
    parser.add_argument(
        "--edits",
        required=True,
        help="Path to the editorial edits JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for the enriched JSON (default: overwrite input)",
    )
    parser.add_argument(
        "--report",
        help="Path to write the editorial report markdown",
    )
    args = parser.parse_args()

    # Load plan data
    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # Load edits
    with open(args.edits, "r", encoding="utf-8-sig") as f:
        edits = json.load(f)

    print(f"Loaded plan: {data.get('week_range', 'unknown')}", file=sys.stderr)
    print(f"Loaded {len(edits.get('day_edits', []))} day edits", file=sys.stderr)

    # Apply edits
    changelog = apply_edits(data, edits)
    print(f"Applied {len(changelog)} editorial changes", file=sys.stderr)

    # Write enriched plan
    output_path = args.output or args.input
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Enriched plan written to {output_path}", file=sys.stderr)

    # Generate report if requested
    if args.report:
        template_dir = Path(__file__).resolve().parent.parent / "templates"
        render_report(changelog, data, template_dir, args.report)


if __name__ == "__main__":
    main()
