#!/usr/bin/env python3
"""Render a nutrition analysis report as markdown from a JSON data file."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_markdown(data, output_path=None):
    """Render nutrition analysis as markdown using Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("nutrition_report.md.j2")

    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = template.render(data)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Nutrition report written to {output_path}", file=sys.stderr)
    else:
        print(md)


def main():
    parser = argparse.ArgumentParser(
        description="Render nutrition analysis report as markdown"
    )
    parser.add_argument("input", help="Path to JSON file with analysis data")
    parser.add_argument(
        "-o", "--output", help="Output markdown file path (default: stdout)"
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded analysis for {len(data.get('dinners', []))} dinners", file=sys.stderr)
    render_markdown(data, args.output)


if __name__ == "__main__":
    main()
