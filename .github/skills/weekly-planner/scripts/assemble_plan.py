#!/usr/bin/env python3
"""Assemble a complete plan_data.json from individual skill outputs.

This script merges the core days configuration with supporting data files
produced by other skills (elevations, parenting, nutrition, etc.) into the
final plan_data.json that the build_plan.py renderer and booklet expect.

Typical usage:
    python assemble_plan.py days.json -o plan_data.json \
        --elevations elevations.json \
        --parenting parenting.json \
        --nutrition nutrition.json

The days.json file must contain the top-level plan structure including
a "days" array and optionally appetizers, salads, beverages, grocery_list,
prep_ahead, and notes.  Supporting files are merged in as follows:

  --elevations   Matched by dinner name into each day's dinner_elevation_tips
  --parenting    Stored as top-level parenting_data
  --nutrition    nutrition.weekly_nutrition_summary stored as nutrition_summary;
                 full object available for future template use
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def get_week_folder(data):
    """Derive the weekly_plans/<YYYY-MM-DD> folder from the plan data."""
    week_range = data.get("week_range", "")
    m = re.match(r"(\w+ \d+)\s*[–—-]\s*\w*\s*\d+,?\s*(\d{4})", week_range)
    if m:
        try:
            start_date = datetime.strptime(f"{m.group(1)}, {m.group(2)}", "%B %d, %Y")
            return start_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def merge_elevations(data, elevations):
    """Match elevation tips to days by dinner name."""
    elev_map = {}
    for e in elevations:
        name = e.get("name", "")
        tips = e.get("elevations", [])
        elev_map[name] = tips
        # Also index by lowercase for fuzzy matching
        elev_map[name.lower()] = tips

    merged_count = 0
    for day in data.get("days", []):
        dinner = day.get("dinner", "")
        tips = elev_map.get(dinner) or elev_map.get(dinner.lower(), [])
        if tips:
            day["dinner_elevation_tips"] = tips
            merged_count += 1
        elif "dinner_elevation_tips" not in day:
            day["dinner_elevation_tips"] = []

    return merged_count


def merge_parenting(data, parenting):
    """Store parenting data at the top level."""
    data["parenting_data"] = parenting


def merge_nutrition(data, nutrition):
    """Extract nutrition summary and store the full analysis."""
    summary = nutrition.get("weekly_nutrition_summary", "")
    if summary:
        data["nutrition_summary"] = summary
    # Store full analysis for templates that want deeper access
    data["nutrition_data"] = nutrition


def main():
    parser = argparse.ArgumentParser(
        description="Assemble plan_data.json from skill outputs"
    )
    parser.add_argument(
        "input",
        help="Path to the core days JSON file containing the plan structure "
             "(must have at minimum a 'days' array and 'week_range')",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for the assembled plan_data.json. "
             "Default: weekly_plans/<date>/plan_data.json",
    )
    parser.add_argument(
        "--elevations",
        help="Path to elevations JSON from the dinner-designer skill. "
             "Each entry is matched to a day by dinner name.",
    )
    parser.add_argument(
        "--parenting",
        help="Path to parenting JSON from the parenting-coach skill.",
    )
    parser.add_argument(
        "--nutrition",
        help="Path to nutrition JSON from the nutrition-coach skill.",
    )
    parser.add_argument(
        "--newsletter",
        help="Path to newsletter JSON from the linkwarden skill.",
    )
    args = parser.parse_args()

    # Load core plan data
    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if "days" not in data:
        print("ERROR: Input JSON must contain a 'days' array", file=sys.stderr)
        sys.exit(1)

    # Inject generation timestamp
    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Merge elevations
    if args.elevations:
        with open(args.elevations, "r", encoding="utf-8-sig") as f:
            elevations = json.load(f)
        count = merge_elevations(data, elevations)
        print(f"Merged elevations: {count}/{len(data['days'])} days matched",
              file=sys.stderr)

    # Merge parenting
    if args.parenting:
        with open(args.parenting, "r", encoding="utf-8-sig") as f:
            parenting = json.load(f)
        merge_parenting(data, parenting)
        print("Merged parenting data", file=sys.stderr)

    # Merge nutrition
    if args.nutrition:
        with open(args.nutrition, "r", encoding="utf-8-sig") as f:
            nutrition = json.load(f)
        merge_nutrition(data, nutrition)
        print("Merged nutrition data", file=sys.stderr)

    # Merge newsletter
    if args.newsletter:
        with open(args.newsletter, "r", encoding="utf-8-sig") as f:
            newsletter = json.load(f)
        data["newsletter_data"] = newsletter
        article_count = len(newsletter.get("clusters", []))
        print(f"Merged newsletter data: {article_count} clusters", file=sys.stderr)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        week_date = get_week_folder(data)
        out_dir = Path("weekly_plans") / week_date
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "plan_data.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write assembled plan
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    days_count = len(data.get("days", []))
    appetizers = len(data.get("appetizers", []))
    salads = len(data.get("salads", []))
    beverages = len(data.get("beverages", []))
    has_parenting = "parenting_data" in data
    has_nutrition = "nutrition_summary" in data
    has_elevations = any(
        d.get("dinner_elevation_tips") for d in data.get("days", [])
    )
    has_newsletter = "newsletter_data" in data

    print(f"Plan assembled: {days_count} days, {appetizers} appetizers, "
          f"{salads} salads, {beverages} beverages", file=sys.stderr)
    print(f"  Parenting: {'✓' if has_parenting else '✗'}  "
          f"Nutrition: {'✓' if has_nutrition else '✗'}  "
          f"Elevations: {'✓' if has_elevations else '✗'}  "
          f"Newsletter: {'✓' if has_newsletter else '✗'}", file=sys.stderr)
    print(f"Written to {out_path}", file=sys.stderr)
    print(f"PLAN_DATA={out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
