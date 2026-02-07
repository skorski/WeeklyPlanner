#!/usr/bin/env python3
"""Render a weekly family plan from a JSON data file to markdown via Jinja2 template."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


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
        help="Output markdown file path (default: stdout)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Inject generation timestamp if not present
    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = render_plan(data)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Weekly plan written to {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
