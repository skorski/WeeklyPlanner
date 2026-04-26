#!/usr/bin/env python3
"""Validate print template/style conventions.

This is intentionally lightweight: it checks the template source for forbidden
inline print styles and, when rendered HTML is provided, verifies key page
archetype requirements from the print style contract.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml


def load_style_contract(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return yaml.safe_load(f) or {}


def check_inline_print_styles(templates_dir: Path, contract: dict) -> list[dict]:
    rules = contract.get("style_rules") or {}
    if not rules.get("forbid_inline_styles_in_partials", False):
        return []

    allow_markers = rules.get("allowlisted_inline_style_patterns") or []
    issues = []
    partials = templates_dir / "partials"
    for path in sorted(partials.glob("print-*.j2")):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "style=" not in line:
                continue
            if any(marker in line for marker in allow_markers):
                continue
            issues.append({
                "severity": "error",
                "check": "inline_print_style",
                "path": str(path),
                "line": line_no,
                "message": "Inline style in print partial; move it to print.css or allowlist it.",
            })
    return issues


def split_page_chunks(html_text: str) -> list[str]:
    return [
        chunk for chunk in re.split(r'(?=<div class="page(?:\s|"))', html_text)
        if chunk.startswith('<div class="page')
    ]


def page_has_class(chunk: str, class_name: str) -> bool:
    opening = chunk.split(">", 1)[0]
    return class_name in opening


def check_rendered_html(html_path: Path, contract: dict) -> list[dict]:
    if not html_path:
        return []

    html_text = html_path.read_text(encoding="utf-8")
    pages = split_page_chunks(html_text)
    issues = []
    archetypes = contract.get("archetypes") or {}
    components = contract.get("components") or {}

    for archetype, spec in archetypes.items():
        page_class = spec.get("page_class")
        if not page_class:
            continue
        matching = [chunk for chunk in pages if page_has_class(chunk, page_class)]
        max_pages = spec.get("max_pages")
        if max_pages and len(matching) > max_pages:
            issues.append({
                "severity": "error",
                "check": "archetype_page_count",
                "path": archetype,
                "message": f"{archetype} renders {len(matching)} pages; max is {max_pages}.",
            })

        for component_name in spec.get("required_components") or []:
            component = components.get(component_name) or {}
            required_class = component.get("class")
            if not required_class:
                continue
            for idx, chunk in enumerate(matching, start=1):
                if required_class not in chunk:
                    issues.append({
                        "severity": "error",
                        "check": "required_component",
                        "path": f"{archetype}[{idx}]",
                        "message": f"Missing required component .{required_class}.",
                    })

    for idx, chunk in enumerate(pages, start=1):
        if page_has_class(chunk, "page-story") and "story-prompt" in chunk:
            if "prompt" not in chunk and "story-prompt" not in chunk:
                issues.append({
                    "severity": "error",
                    "check": "story_prompt",
                    "path": f"page[{idx}]",
                    "message": "Story prompt is missing shared prompt class.",
                })

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate print style conventions")
    parser.add_argument(
        "--templates",
        default=str(Path(__file__).resolve().parent.parent / "templates"),
        help="Booklet templates directory",
    )
    parser.add_argument(
        "--contract",
        default=str(Path(__file__).resolve().parent.parent / "contracts" / "print_style.yaml"),
        help="Path to print_style.yaml",
    )
    parser.add_argument("--html", help="Optional rendered weekly-plan.html")
    parser.add_argument("-o", "--output", help="Output print-style-report.json")
    args = parser.parse_args()

    templates_dir = Path(args.templates)
    contract_path = Path(args.contract)
    html_path = Path(args.html) if args.html else None
    output_path = Path(args.output) if args.output else Path("print-style-report.json")

    contract = load_style_contract(contract_path)
    issues = []
    issues.extend(check_inline_print_styles(templates_dir, contract))
    if html_path:
        issues.extend(check_rendered_html(html_path, contract))

    report = {
        "status": "FAIL" if any(i["severity"] == "error" for i in issues) else "PASS",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "contract": str(contract_path),
        "templates": str(templates_dir),
        "html": str(html_path) if html_path else None,
        "issues": issues,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"PRINT_STYLE_REPORT={output_path}", file=sys.stderr)
    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
