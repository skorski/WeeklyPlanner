#!/usr/bin/env python3
"""Look up FCPS school calendar events for a given date range."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CAL_PATH = SKILL_DIR / "references" / "fcps_2025_2026.json"


def load_calendar():
    with open(CAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup_week(start_date: str, end_date: str):
    """Return school events (no-school days, early releases) within a date range."""
    cal = load_calendar()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    results = {"no_school": [], "early_release": []}

    for entry in cal["no_school"]:
        d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if start <= d <= end:
            results["no_school"].append(entry)

    for entry in cal["early_release"]:
        d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if start <= d <= end:
            results["early_release"].append(entry)

    return results


def main():
    parser = argparse.ArgumentParser(description="Look up FCPS school calendar for a date range")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    args = parser.parse_args()

    results = lookup_week(args.start, args.end)

    output = json.dumps(results, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"School calendar events written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
