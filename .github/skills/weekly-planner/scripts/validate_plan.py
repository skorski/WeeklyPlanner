#!/usr/bin/env python3
"""Validate a canonical weekly plan against the section registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from contracts.canonicalize import canonicalize_plan_data
from contracts.registry import load_section_registry, load_yaml_or_json
from contracts.section_manifest import write_manifest
from contracts.validation import validate_plan_data


def _load_optional_json(path: str | None) -> dict | None:
    if not path:
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate plan_data.json against section contracts")
    parser.add_argument("plan_data", help="Path to plan_data.json")
    parser.add_argument("--registry", help="Path to section_registry.yaml")
    parser.add_argument("--run-request", help="Optional week_request.json")
    parser.add_argument("--history", help="Optional history_snapshot.json")
    parser.add_argument("--reading-sources", help="Optional reading_sources.json")
    parser.add_argument("--output", help="Write validation report JSON here")
    parser.add_argument("--manifest-output", help="Write section_manifest.json here")
    parser.add_argument("--write-canonical", help="Write canonicalized plan data here")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as errors")
    args = parser.parse_args()

    with open(args.plan_data, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    plan_data, aliases = canonicalize_plan_data(raw)
    registry = load_section_registry(args.registry)
    run_request = _load_optional_json(args.run_request)
    history = _load_optional_json(args.history)
    reading_sources = _load_optional_json(args.reading_sources)
    report = validate_plan_data(
        plan_data,
        registry,
        run_request=run_request,
        history=history,
        reading_sources=reading_sources,
        aliases_applied=aliases,
    )

    if args.write_canonical:
        Path(args.write_canonical).write_text(
            json.dumps(plan_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if args.manifest_output:
        write_manifest(report["section_manifest"], args.manifest_output)
    if args.output:
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    failed = report["status"] == "FAIL" or (args.strict and report["warnings"])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

