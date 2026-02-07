#!/usr/bin/env python3
"""Render recipe recommendations as markdown from a JSON candidate list."""

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

from jinja2 import Environment, FileSystemLoader


def render_markdown(recipes, prompt, output_path=None):
    """Render recipe list as markdown using Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("menu_suggestions.md.j2")

    # Split by category
    dinners = [r for r in recipes if r.get("category") == "dinner"]
    appetizers = [r for r in recipes if r.get("category") == "appetizer"]
    salads = [r for r in recipes if r.get("category") == "salad"]
    beverages = [r for r in recipes if r.get("category") == "beverage"]

    # Split salads into dinner-sized and sides
    dinner_salads = [s for s in salads if s.get("salad_type") in ("composed_dinner", "tossed_dinner")]
    side_salads = [s for s in salads if s.get("salad_type") not in ("composed_dinner", "tossed_dinner")]

    context = {
        "prompt": prompt,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dinners": dinners,
        "appetizers": appetizers,
        "salads": salads,
        "dinner_salads": dinner_salads,
        "side_salads": side_salads,
        "beverages": beverages,
        "total": len(recipes),
    }

    md = template.render(context)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Menu suggestions written to {output_path}", file=sys.stderr)
    else:
        print(md)


def main():
    parser = argparse.ArgumentParser(description="Render recipe recommendations as markdown")
    parser.add_argument("input", help="Path to JSON file with recipe candidates")
    parser.add_argument("-p", "--prompt", default="Weekly menu", help="The original search prompt")
    parser.add_argument("-o", "--output", help="Output markdown file path (default: stdout)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8-sig") as f:
        recipes = json.load(f)

    print(f"Loaded {len(recipes)} recipes", file=sys.stderr)
    render_markdown(recipes, args.prompt, args.output)


if __name__ == "__main__":
    main()
