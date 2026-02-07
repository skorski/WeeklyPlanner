#!/usr/bin/env python3
"""Render elevated recipe recommendations as markdown from a JSON list."""

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

from jinja2 import Environment, FileSystemLoader


def render_markdown(recipes, output_path=None):
    """Render elevated recipe list as markdown using Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("elevated_menu.md.j2")

    # Collect all unique extra ingredients across elevations
    pantry_items = set()
    for r in recipes:
        for e in r.get("elevations", []):
            for item in e.get("extra_ingredients", []):
                pantry_items.add(item)

    context = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "recipes": recipes,
        "total": len(recipes),
        "pantry_items": sorted(pantry_items),
    }

    md = template.render(context)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Elevated menu written to {output_path}", file=sys.stderr)
    else:
        print(md)


def main():
    parser = argparse.ArgumentParser(description="Render elevated recipes as markdown")
    parser.add_argument("input", help="Path to JSON file with elevation data")
    parser.add_argument("-o", "--output", help="Output markdown file path (default: stdout)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    print(f"Loaded {len(recipes)} recipes", file=sys.stderr)
    render_markdown(recipes, args.output)


if __name__ == "__main__":
    main()
