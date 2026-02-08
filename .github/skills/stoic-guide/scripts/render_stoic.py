#!/usr/bin/env python3
"""Render stoic guide JSON data into a readable markdown file.

Usage:
    python render_stoic.py stoic_data.json -o stoic-guide.md
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("ERROR: jinja2 is required. Install with: pip install jinja2", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Render stoic guide markdown")
    parser.add_argument("input", help="Path to stoic JSON data file")
    parser.add_argument("-o", "--output", help="Output markdown file path")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)
    template = env.get_template("stoic_guide.md.j2")

    rendered = template.render(**data)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"Written to {out_path}", file=sys.stderr)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
