from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .registry import path_count, resolve_path


def _context_for_path(path: str, plan_data: dict[str, Any], run_request: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    if path.startswith("run_request."):
        return (run_request or {}), path.removeprefix("run_request.")
    return plan_data, path


def _condition_passes(condition: dict[str, Any], plan_data: dict[str, Any], run_request: dict[str, Any] | None) -> bool:
    data, path = _context_for_path(condition.get("path", ""), plan_data, run_request)
    count = path_count(data, path)
    if "min_count" in condition and count < int(condition["min_count"]):
        return False
    if "max_count" in condition and count > int(condition["max_count"]):
        return False
    if "exact" in condition and count != int(condition["exact"]):
        return False
    if not any(k in condition for k in ("min_count", "max_count", "exact")):
        return count > 0
    return True


def conditions_active(section: dict[str, Any], plan_data: dict[str, Any], run_request: dict[str, Any] | None = None) -> bool:
    required = section.get("required", "optional")
    if required == "always":
        return True
    if required == "optional":
        return False
    conditions = section.get("conditions") or {}
    if not conditions:
        return False
    if "any" in conditions:
        return any(_condition_passes(c, plan_data, run_request) for c in conditions["any"])
    if "all" in conditions:
        return all(_condition_passes(c, plan_data, run_request) for c in conditions["all"])
    return _condition_passes(conditions, plan_data, run_request)


def build_section_manifest(
    plan_data: dict[str, Any],
    registry: dict[str, Any],
    *,
    run_request: dict[str, Any] | None = None,
    aliases_applied: list[str] | None = None,
) -> dict[str, Any]:
    sections = []
    for section in registry.get("sections", []):
        active = conditions_active(section, plan_data, run_request)
        missing_paths = []
        count_issues = []
        counts = {}

        if active:
            for path in section.get("required_paths", []):
                data, resolved_path = _context_for_path(path, plan_data, run_request)
                if path_count(data, resolved_path) == 0:
                    missing_paths.append(path)

            for item_count in section.get("item_counts", []):
                path = item_count["path"]
                data, resolved_path = _context_for_path(path, plan_data, run_request)
                count = path_count(data, resolved_path)
                counts[path] = count
                if "exact" in item_count and count != int(item_count["exact"]):
                    count_issues.append(f"{path}: expected {item_count['exact']}, found {count}")
                if "min" in item_count and count < int(item_count["min"]):
                    count_issues.append(f"{path}: expected at least {item_count['min']}, found {count}")
                if "max" in item_count and count > int(item_count["max"]):
                    count_issues.append(f"{path}: expected at most {item_count['max']}, found {count}")

        status = "skip"
        if active:
            status = "fail" if missing_paths or count_issues else "pass"

        sections.append({
            "id": section.get("id"),
            "title": section.get("title"),
            "required": section.get("required"),
            "active": active,
            "status": status,
            "source_paths": section.get("source_paths", []),
            "render_targets": section.get("render_targets", []),
            "render_selectors": section.get("render_selectors", {}),
            "print_fit_policy": section.get("print_fit_policy", {}),
            "style_profile": section.get("style_profile"),
            "counts": counts,
            "missing_paths": missing_paths,
            "issues": count_issues,
        })

    return {
        "schema_version": registry.get("schema_version", "1.0"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "week_range": plan_data.get("week_range", ""),
        "aliases_applied": aliases_applied or [],
        "sections": sections,
    }


def manifest_failures(manifest: dict[str, Any]) -> list[str]:
    failures = []
    for section in manifest.get("sections", []):
        if section.get("status") == "fail":
            details = []
            if section.get("missing_paths"):
                details.append("missing " + ", ".join(section["missing_paths"]))
            if section.get("issues"):
                details.extend(section["issues"])
            failures.append(f"{section.get('id')}: {'; '.join(details)}")
    return failures


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

