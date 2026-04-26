#!/usr/bin/env python3
"""Create a print-fit copy of plan_data.json.

The formatter keeps the full source plan untouched, writes plan_data_print.json,
and records deterministic trims in print-format-report.json. It uses the shared
section registry and proofreader so print section budgets are enforced against
the same contract used by assembly.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
WEEKLY_PLANNER_DIR = SKILLS_DIR / "weekly-planner"
sys.path.insert(0, str(WEEKLY_PLANNER_DIR))

from contracts.canonicalize import canonicalize_plan_data
from contracts.registry import load_section_registry
from contracts.section_manifest import write_manifest
from contracts.validation import validate_plan_data


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def trim_text(value, max_chars: int):
    if not isinstance(value, str) or len(value) <= max_chars:
        return value, False
    cut = value[: max_chars - 3].rsplit(" ", 1)[0].rstrip()
    return f"{cut}...", True


def trim_weekly_read(data: dict, cap: int, report: list[dict]) -> bool:
    changed = False
    newsletter = data.get("newsletter_data")
    if not isinstance(newsletter, dict):
        return False

    clusters = newsletter.get("clusters") or []
    for idx, cluster in enumerate(clusters):
        if not isinstance(cluster, dict):
            continue
        before = cluster.get("synthesis")
        cluster["synthesis"], did_trim = trim_text(before, cap)
        if did_trim:
            changed = True
            report.append({
                "section": "weekly_read",
                "path": f"newsletter_data.clusters[{idx}].synthesis",
                "from_chars": len(before),
                "to_chars": len(cluster["synthesis"]),
            })
        for article_idx, article in enumerate(cluster.get("articles") or []):
            if not isinstance(article, dict):
                continue
            before = article.get("one_liner")
            article["one_liner"], did_trim = trim_text(before, 140)
            if did_trim:
                changed = True
                report.append({
                    "section": "weekly_read",
                    "path": f"newsletter_data.clusters[{idx}].articles[{article_idx}].one_liner",
                    "from_chars": len(before),
                    "to_chars": len(article["one_liner"]),
                })

    before = newsletter.get("reflections")
    newsletter["reflections"], did_trim = trim_text(before, 650)
    if did_trim:
        changed = True
        report.append({
            "section": "weekly_read",
            "path": "newsletter_data.reflections",
            "from_chars": len(before),
            "to_chars": len(newsletter["reflections"]),
        })

    fun = newsletter.get("fun_section")
    if isinstance(fun, dict):
        before = fun.get("content")
        fun["content"], did_trim = trim_text(before, 350)
        if did_trim:
            changed = True
            report.append({
                "section": "weekly_read",
                "path": "newsletter_data.fun_section.content",
                "from_chars": len(before),
                "to_chars": len(fun["content"]),
            })

    return changed


def trim_stoic(data: dict, report: list[dict]) -> bool:
    changed = False
    stoic = data.get("stoic_data")
    if not isinstance(stoic, dict):
        return False

    for path, cap in (
        ("introduction", 520),
        ("closing_thought", 280),
    ):
        before = stoic.get(path)
        stoic[path], did_trim = trim_text(before, cap)
        if did_trim:
            changed = True
            report.append({
                "section": "stoic_guide",
                "path": f"stoic_data.{path}",
                "from_chars": len(before),
                "to_chars": len(stoic[path]),
            })

    for idx, meditation in enumerate(stoic.get("meditations") or []):
        if not isinstance(meditation, dict):
            continue
        for field, cap in (("reflection", 420), ("prompt", 180)):
            before = meditation.get(field)
            meditation[field], did_trim = trim_text(before, cap)
            if did_trim:
                changed = True
                report.append({
                    "section": "stoic_guide",
                    "path": f"stoic_data.meditations[{idx}].{field}",
                    "from_chars": len(before),
                    "to_chars": len(meditation[field]),
                })

    return changed


def trim_nutrition(data: dict, report: list[dict]) -> bool:
    changed = False
    before = data.get("nutrition_summary")
    data["nutrition_summary"], did_trim = trim_text(before, 700)
    if did_trim:
        changed = True
        report.append({
            "section": "nutrition",
            "path": "nutrition_summary",
            "from_chars": len(before),
            "to_chars": len(data["nutrition_summary"]),
        })

    nutrition = data.get("nutrition_data")
    if isinstance(nutrition, dict):
        primer = nutrition.get("nutrient_primer")
        if isinstance(primer, list):
            for idx, item in enumerate(primer):
                if not isinstance(item, dict):
                    continue
                before = item.get("why_it_matters")
                item["why_it_matters"], did_trim = trim_text(before, 260)
                if did_trim:
                    changed = True
                    report.append({
                        "section": "nutrition",
                        "path": f"nutrition_data.nutrient_primer[{idx}].why_it_matters",
                        "from_chars": len(before),
                        "to_chars": len(item["why_it_matters"]),
                    })

    return changed


def render_and_proof(data: dict, registry: dict, tmp_dir: Path) -> dict:
    data_path = tmp_dir / "plan_data_print.json"
    manifest_path = tmp_dir / "section_manifest.json"
    write_json(data_path, data)

    validation_report = validate_plan_data(data, registry)
    write_manifest(validation_report["section_manifest"], manifest_path)

    render_script = SKILLS_DIR / "booklet" / "scripts" / "render_booklet.py"
    proof_script = SKILLS_DIR / "proofreader" / "scripts" / "proofread.py"
    subprocess.run(
        [sys.executable, str(render_script), str(data_path), "-o", str(tmp_dir), "--html-only"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    proof = subprocess.run(
        [
            sys.executable,
            str(proof_script),
            str(data_path),
            str(tmp_dir / "weekly-plan.html"),
            "--manifest",
            str(manifest_path),
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proof.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "proofreader did not return JSON\n"
            f"stdout:\n{proof.stdout}\n"
            f"stderr:\n{proof.stderr}"
        ) from exc


def needs_weekly_read_trim(proof: dict) -> bool:
    issues = proof.get("section_marker_issues") or []
    return any("weekly_read" in issue and "OVER BUDGET" in issue for issue in issues)


def needs_stoic_trim(proof: dict) -> bool:
    return any("page-stoic" in issue.get("classes", "") for issue in proof.get("overflow") or [])


def needs_nutrition_trim(proof: dict) -> bool:
    return any("page-nutrition" in issue.get("classes", "") for issue in proof.get("overflow") or [])


def has_print_failures(proof: dict) -> bool:
    return bool(
        any(o.get("is_bounded_page") for o in proof.get("overflow") or [])
        or proof.get("section_marker_issues")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a print-fit plan_data_print.json")
    parser.add_argument("input", help="Path to canonical or assembled plan_data.json")
    parser.add_argument("-o", "--output", help="Output plan_data_print.json path")
    parser.add_argument("--report", help="Output print-format-report.json path")
    parser.add_argument("--registry", help="Path to section_registry.yaml")
    parser.add_argument("--max-iterations", type=int, default=6)
    parser.add_argument("--no-render-check", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name("plan_data_print.json")
    report_path = Path(args.report) if args.report else output_path.with_name("print-format-report.json")

    original = load_json(input_path)
    data, aliases_applied = canonicalize_plan_data(deepcopy(original))
    registry = load_section_registry(args.registry)

    changes: list[dict] = []
    iterations: list[dict] = []
    caps = [1200, 900, 650, 450, 300, 220]
    final_proof = None

    if not args.no_render_check:
        with tempfile.TemporaryDirectory(prefix="weekly-print-fit-") as tmp:
            tmp_dir = Path(tmp)
            for iteration in range(args.max_iterations):
                proof = render_and_proof(data, registry, tmp_dir)
                final_proof = proof
                iteration_report = {
                    "iteration": iteration,
                    "passed": not has_print_failures(proof),
                    "overflow": proof.get("overflow") or [],
                    "section_marker_issues": proof.get("section_marker_issues") or [],
                }
                iterations.append(iteration_report)
                if not has_print_failures(proof):
                    break

                changed = False
                if needs_weekly_read_trim(proof):
                    changed = trim_weekly_read(data, caps[min(iteration, len(caps) - 1)], changes) or changed
                if needs_stoic_trim(proof):
                    changed = trim_stoic(data, changes) or changed
                if needs_nutrition_trim(proof):
                    changed = trim_nutrition(data, changes) or changed

                if not changed:
                    break
    else:
        trim_weekly_read(data, 900, changes)
        trim_stoic(data, changes)
        trim_nutrition(data, changes)

    write_json(output_path, data)

    validation_report = validate_plan_data(data, registry, aliases_applied=aliases_applied)
    manifest_path = output_path.with_name("section_manifest_print.json")
    write_manifest(validation_report["section_manifest"], manifest_path)

    status = "PASS"
    if final_proof and has_print_failures(final_proof):
        status = "FAIL"
    if validation_report["status"] == "FAIL":
        status = "FAIL"

    report = {
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(input_path),
        "output": str(output_path),
        "section_manifest": str(manifest_path),
        "aliases_applied": aliases_applied,
        "changes": changes,
        "iterations": iterations,
        "validation_status": validation_report["status"],
        "final_proof": final_proof,
    }
    write_json(report_path, report)

    print(f"PRINT_DATA={output_path}", file=sys.stderr)
    print(f"PRINT_FORMAT_REPORT={report_path}", file=sys.stderr)
    print(f"PRINT_SECTION_MANIFEST={manifest_path}", file=sys.stderr)
    if status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
