#!/usr/bin/env python3
"""Render recipe cards as markdown from a JSON file."""

import argparse
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_markdown(recipe_cards, output_path=None):
    """Render recipe cards as markdown using Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("recipe_cards.md.j2")

    md = template.render(recipe_cards=recipe_cards)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Recipe cards written to {output_path}", file=sys.stderr)
    else:
        print(md)


def main():
    parser = argparse.ArgumentParser(description="Render recipe cards as markdown")
    parser.add_argument(
        "input",
        help="Path to JSON file with recipe cards (object with 'recipe_cards' array)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output markdown file path (default: stdout)",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    cards = data.get("recipe_cards", data) if isinstance(data, dict) else data
    print(f"Loaded {len(cards)} recipe cards", file=sys.stderr)
    render_markdown(cards, args.output)


if __name__ == "__main__":
    main()
