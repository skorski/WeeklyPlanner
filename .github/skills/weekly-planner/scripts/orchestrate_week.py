#!/usr/bin/env python3
"""Durable weekly-planner orchestration entry point.

This CLI owns deterministic stage state, artifact locations, and validation
gates. Model-backed skill execution is isolated behind the optional Copilot SDK
adapter so the contract/validation pipeline remains usable without SDK access.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
WEEKLY_PLANNER_DIR = SKILLS_DIR / "weekly-planner"


STAGES = [
    "input_review",
    "wave_1_research",
    "dinner_album_selection",
    "wave_2_research",
    "section_validation",
    "markdown_review",
    "print_format",
    "print_review",
    "final_qa",
]


def load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def run_command(command: list[str], cwd: Path = REPO_ROOT) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def sdk_available() -> bool:
    return any(importlib.util.find_spec(name) for name in ("copilot", "copilot_sdk"))


def default_week_dir(week_start: str | None) -> Path:
    if week_start:
        return REPO_ROOT / "weekly_plans" / week_start
    return REPO_ROOT / "weekly_plans" / datetime.now().strftime("%Y-%m-%d")


def build_manifest(args, request: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = existing or {}
    manifest.setdefault("schema_version", "1.0")
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    manifest.setdefault("created_at", manifest["updated_at"])
    manifest["week_start"] = args.week_start
    manifest["week_dir"] = str(args.week_dir)
    manifest["prompt"] = str(args.prompt) if args.prompt else None
    manifest["week_request"] = str(args.week_request) if args.week_request else None
    manifest["interactive"] = bool(args.interactive)
    manifest["sdk_enabled"] = bool(args.enable_sdk)
    manifest["sdk_available"] = sdk_available()
    manifest["request"] = request
    manifest.setdefault("stages", [
        {"id": stage, "status": "pending", "artifacts": [], "messages": []}
        for stage in STAGES
    ])
    return manifest


def stage(manifest: dict[str, Any], stage_id: str) -> dict[str, Any]:
    for item in manifest["stages"]:
        if item["id"] == stage_id:
            return item
    item = {"id": stage_id, "status": "pending", "artifacts": [], "messages": []}
    manifest["stages"].append(item)
    return item


def mark_stage(
    manifest: dict[str, Any],
    stage_id: str,
    status: str,
    *,
    artifact: Path | None = None,
    message: str | None = None,
) -> None:
    item = stage(manifest, stage_id)
    item["status"] = status
    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if artifact:
        artifacts = item.setdefault("artifacts", [])
        artifact_text = str(artifact)
        if artifact_text not in artifacts:
            artifacts.append(artifact_text)
    if message:
        item.setdefault("messages", []).append(message)


def prepare_inputs(args, request: dict[str, Any], manifest: dict[str, Any]) -> None:
    args.week_dir.mkdir(parents=True, exist_ok=True)
    if args.week_request:
        target = args.week_dir / "week_request.json"
        if Path(args.week_request).resolve() != target.resolve():
            shutil.copyfile(args.week_request, target)
        mark_stage(manifest, "input_review", "pass", artifact=target)
    else:
        mark_stage(manifest, "input_review", "pending", message="No structured week_request.json provided.")

    if request.get("weekly_read"):
        reading_script = SKILLS_DIR / "linkwarden" / "scripts" / "fetch_reading_sources.py"
        reading_sources = args.week_dir / "reading_sources.json"
        reading_report = args.week_dir / "reading_ingestion_report.json"
        result = run_command([
            sys.executable,
            str(reading_script),
            "--input",
            str(args.week_dir / "week_request.json"),
            "-o",
            str(reading_sources),
            "--report",
            str(reading_report),
        ])
        status = "pass" if result["returncode"] == 0 else "fail"
        mark_stage(manifest, "wave_1_research", status, artifact=reading_sources, message="reading source ingestion")
        if result["returncode"] != 0:
            mark_stage(manifest, "wave_1_research", "fail", message=result["stderr"] or result["stdout"])

    if request.get("news_feed"):
        news_script = SKILLS_DIR / "news-feed" / "scripts" / "fetch_news_feed.py"
        news_markdown = args.week_dir / "news-feed.md"
        news_report = args.week_dir / "news_feed_report.json"
        result = run_command([
            sys.executable,
            str(news_script),
            "--input",
            str(args.week_dir / "week_request.json"),
            "-o",
            str(news_markdown),
            "--report",
            str(news_report),
        ])
        status = "pass" if result["returncode"] == 0 else "fail"
        mark_stage(manifest, "wave_1_research", status, artifact=news_markdown, message="news feed ingestion")
        if result["returncode"] != 0:
            mark_stage(manifest, "wave_1_research", "fail", message=result["stderr"] or result["stdout"])

    history_script = WEEKLY_PLANNER_DIR / "scripts" / "collect_history.py"
    history_path = args.week_dir / "history_snapshot.json"
    history_cmd = [
        sys.executable,
        str(history_script),
        "--root",
        str(REPO_ROOT),
        "-o",
        str(history_path),
    ]
    if args.week_start:
        history_cmd.extend(["--before", args.week_start])
    result = run_command(history_cmd)
    status = "pass" if result["returncode"] == 0 else "fail"
    mark_stage(manifest, "wave_1_research", status, artifact=history_path, message="history snapshot")
    if result["returncode"] != 0:
        mark_stage(manifest, "wave_1_research", "fail", message=result["stderr"] or result["stdout"])


def require_sdk(args, manifest: dict[str, Any]) -> bool:
    if not args.enable_sdk:
        return False
    if sdk_available():
        return True
    mark_stage(
        manifest,
        "wave_1_research",
        "blocked",
        message="Copilot SDK Python package is not installed; deterministic preparation completed only.",
    )
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate the weekly planner pipeline")
    parser.add_argument("--prompt", help="masterPrompt.md or another freeform prompt document")
    parser.add_argument("--week-request", help="Structured week_request.json")
    parser.add_argument("--week-start", help="Starting Sunday as YYYY-MM-DD")
    parser.add_argument("--week-dir", type=Path, help="Output week directory")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--from-stage", choices=STAGES)
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare deterministic artifacts")
    parser.add_argument("--enable-sdk", action="store_true", help="Enable Copilot SDK-backed skill sessions")
    args = parser.parse_args()

    args.prompt = Path(args.prompt) if args.prompt else None
    args.week_request = Path(args.week_request) if args.week_request else None
    args.week_dir = args.week_dir or default_week_dir(args.week_start)
    run_manifest_path = args.week_dir / "run_manifest.json"

    existing = load_json(run_manifest_path) if args.resume and run_manifest_path.exists() else None
    request = load_json(args.week_request)
    manifest = build_manifest(args, request, existing=existing)

    prepare_inputs(args, request, manifest)

    if args.prepare_only or not args.enable_sdk:
        mark_stage(
            manifest,
            "wave_1_research",
            stage(manifest, "wave_1_research").get("status", "pending"),
            message="Prepared deterministic artifacts; SDK skill execution not requested.",
        )
        write_json(run_manifest_path, manifest)
        print(f"RUN_MANIFEST={run_manifest_path}", file=sys.stderr)
        return

    if not require_sdk(args, manifest):
        write_json(run_manifest_path, manifest)
        print(f"RUN_MANIFEST={run_manifest_path}", file=sys.stderr)
        sys.exit(1)

    mark_stage(
        manifest,
        "wave_1_research",
        "blocked",
        message="SDK package detected; skill-session adapter is intentionally isolated for the next implementation pass.",
    )
    write_json(run_manifest_path, manifest)
    print(f"RUN_MANIFEST={run_manifest_path}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
