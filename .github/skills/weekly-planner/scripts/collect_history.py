#!/usr/bin/env python3
"""Collect recent weekly-plan history for dedupe-aware researchers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from contracts.canonicalize import canonicalize_plan_data


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _ngrams(text: str, n: int = 5) -> list[str]:
    words = re.findall(r"[A-Za-z']+", text.lower())
    return [" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))]


def collect_history(root: Path, before: str | None = None, limit: int = 8) -> dict[str, Any]:
    plan_paths = sorted(root.glob("weekly_plans/*/plan_data.json"))
    if before:
        plan_paths = [p for p in plan_paths if p.parent.name < before]
    plan_paths = plan_paths[-limit:]

    history: dict[str, Any] = {
        "plans": [],
        "dinners": [],
        "albums": [],
        "parenting_themes": [],
        "parenting_questions": [],
        "parenting_nudges": [],
        "stoic_themes": [],
        "stoic_categories": [],
        "stoic_anchor_quotes": [],
        "principles_themes": [],
        "principles_thinkers": [],
        "newsletter_themes": [],
        "newsletter_urls": [],
        "story_titles": [],
        "story_lessons": [],
        "story_ngrams": [],
    }

    for path in plan_paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        data, aliases = canonicalize_plan_data(raw)
        history["plans"].append({
            "week": path.parent.name,
            "week_range": data.get("week_range", ""),
            "aliases_applied": aliases,
        })

        for day in _list(data.get("days")):
            if not isinstance(day, dict):
                continue
            if day.get("dinner"):
                history["dinners"].append(day["dinner"])
            if day.get("album"):
                history["albums"].append(day["album"])

        parenting = data.get("parenting_data") or {}
        if isinstance(parenting, dict):
            theme = parenting.get("weekly_theme") or {}
            if isinstance(theme, dict) and theme.get("title"):
                history["parenting_themes"].append(theme["title"])
            for q in _list(parenting.get("dinner_questions")):
                if isinstance(q, dict) and q.get("question"):
                    history["parenting_questions"].append(q["question"])
            for nudge in _list(parenting.get("nudges")):
                if isinstance(nudge, dict) and nudge.get("title"):
                    history["parenting_nudges"].append(nudge["title"])

        stoic = data.get("stoic_data") or {}
        if isinstance(stoic, dict):
            theme = stoic.get("theme") or {}
            if isinstance(theme, dict):
                if theme.get("title"):
                    history["stoic_themes"].append(theme["title"])
                if theme.get("category"):
                    history["stoic_categories"].append(theme["category"])
            anchor = stoic.get("anchor_quote") or {}
            if isinstance(anchor, dict) and anchor.get("text"):
                history["stoic_anchor_quotes"].append(anchor["text"])

        principles = data.get("principles_data") or {}
        if isinstance(principles, dict):
            theme = principles.get("theme") or {}
            if isinstance(theme, dict):
                if theme.get("title"):
                    history["principles_themes"].append(theme["title"])
                if theme.get("primary_thinker"):
                    history["principles_thinkers"].append(theme["primary_thinker"])

        newsletter = data.get("newsletter_data") or {}
        if isinstance(newsletter, dict):
            for cluster in _list(newsletter.get("clusters")):
                if isinstance(cluster, dict):
                    if cluster.get("theme"):
                        history["newsletter_themes"].append(cluster["theme"])
                    for article in _list(cluster.get("articles")):
                        if isinstance(article, dict) and article.get("url"):
                            history["newsletter_urls"].append(article["url"])

        story = data.get("child_wisdom") or {}
        if isinstance(story, dict):
            if story.get("title"):
                history["story_titles"].append(story["title"])
            if story.get("life_lesson"):
                history["story_lessons"].append(story["life_lesson"])
            if story.get("story"):
                history["story_ngrams"].extend(_ngrams(story["story"])[:400])

    for key, value in list(history.items()):
        if isinstance(value, list) and key != "plans":
            history[key] = list(dict.fromkeys(value))
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect history from prior weekly plans")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--before", help="Only include plan folders before this YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=8, help="Number of prior plans to include")
    parser.add_argument("-o", "--output", help="Output JSON path")
    args = parser.parse_args()

    history = collect_history(Path(args.root), before=args.before, limit=args.limit)
    output = json.dumps(history, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
