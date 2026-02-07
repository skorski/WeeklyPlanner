#!/usr/bin/env python3
"""Render a weekly family plan from a JSON data file to markdown via Jinja2 template.

All output is placed in weekly_plans/<YYYY-MM-DD>/ where the date is the
starting Sunday of the plan week.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def get_week_folder(data):
    """Derive the weekly_plans/<YYYY-MM-DD> folder from the plan data.

    Looks for the starting Sunday date in `week_range` (e.g. "February 8 – 14, 2026").
    Falls back to today if parsing fails.
    """
    week_range = data.get("week_range", "")
    # Try to extract a full date from patterns like "February 8 – 14, 2026"
    m = re.match(r"(\w+ \d+)\s*[–—-]\s*\w*\s*\d+,?\s*(\d{4})", week_range)
    if m:
        try:
            start_date = datetime.strptime(f"{m.group(1)}, {m.group(2)}", "%B %d, %Y")
            return start_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Fallback: use today
    return datetime.now().strftime("%Y-%m-%d")


def render_plan(data, template_name="weekly_plan.md.j2"):
    """Render markdown from a Jinja2 template and plan data dict."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template(template_name)
    return template.render(data)


def main():
    parser = argparse.ArgumentParser(
        description="Render weekly family plan markdown from JSON data"
    )
    parser.add_argument(
        "input",
        help="Path to JSON data file with the plan information",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output filename (placed inside weekly_plans/<date>/ folder). "
             "Default: weekly-plan.md",
        default="weekly-plan.md",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # Inject generation timestamp if not present
    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Determine output folder: weekly_plans/<YYYY-MM-DD>/
    week_date = get_week_folder(data)
    out_dir = Path("weekly_plans") / week_date
    out_dir.mkdir(parents=True, exist_ok=True)

    md = render_plan(data)

    out_path = out_dir / os.path.basename(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    # Print the folder path so the agent knows where files live
    print(f"Weekly plan written to {out_path}", file=sys.stderr)
    print(f"PLAN_DIR={out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
