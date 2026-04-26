from __future__ import annotations

import copy
from typing import Any


def _set_if_absent(target: dict[str, Any], key: str, value: Any, aliases: list[str], label: str) -> None:
    if value is None:
        return
    if key not in target or target.get(key) in (None, "", [], {}):
        target[key] = value
        aliases.append(label)


def _move_top_level(data: dict[str, Any], source: str, dest: str, aliases: list[str]) -> None:
    if source in data and dest not in data:
        data[dest] = data[source]
        aliases.append(f"{source} -> {dest}")


def canonicalize_plan_data(plan_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a canonicalized copy of plan_data and alias notes.

    This function is intentionally conservative: it only maps known historical
    drift fields and leaves unknown content untouched for validation to report.
    """
    data = copy.deepcopy(plan_data)
    aliases: list[str] = []

    _move_top_level(data, "parenting", "parenting_data", aliases)
    _move_top_level(data, "newsletter", "newsletter_data", aliases)
    _move_top_level(data, "news_feed", "news_feed_data", aliases)
    _move_top_level(data, "stoic_guide", "stoic_data", aliases)
    _move_top_level(data, "principles_guide", "principles_data", aliases)
    _move_top_level(data, "nutrition", "nutrition_data", aliases)

    if "elsie_no_go" in data and "elsie_no_list" not in data:
        data["elsie_no_list"] = data["elsie_no_go"]
        aliases.append("elsie_no_go -> elsie_no_list")

    for story_key in ("story_data", "story"):
        story = data.get(story_key)
        if isinstance(story, dict) and "child_wisdom" not in data and story.get("story"):
            data["child_wisdom"] = story
            aliases.append(f"{story_key} -> child_wisdom")

    parenting = data.get("parenting_data")
    if isinstance(parenting, dict):
        _set_if_absent(
            parenting,
            "dinner_questions",
            parenting.get("conversation_starters"),
            aliases,
            "parenting_data.conversation_starters -> parenting_data.dinner_questions",
        )
        _set_if_absent(
            parenting,
            "nudges",
            parenting.get("parenting_nudges"),
            aliases,
            "parenting_data.parenting_nudges -> parenting_data.nudges",
        )
        if isinstance(parenting.get("dinner_questions"), list):
            question_by_day: dict[str, dict[str, Any]] = {}
            for question in parenting["dinner_questions"]:
                if isinstance(question, dict) and "question" not in question and "text" in question:
                    question["question"] = question["text"]
                    aliases.append("parenting_data.dinner_questions[].text -> question")
                if isinstance(question, dict):
                    day = str(question.get("day") or question.get("day_of_week") or "").strip().lower()
                    if day:
                        question_by_day[day] = question
            for day in data.get("days", []) if isinstance(data.get("days"), list) else []:
                if not isinstance(day, dict):
                    continue
                if isinstance(day.get("dinner_question"), dict) and day["dinner_question"].get("question"):
                    continue
                dow = str(day.get("day_of_week") or day.get("long_name") or day.get("name") or "").split(",")[0].split()[0].strip().lower()
                match = question_by_day.get(dow)
                if not match:
                    for key, value in question_by_day.items():
                        if key.startswith(dow[:3]) or dow.startswith(key[:3]):
                            match = value
                            break
                if match:
                    day["dinner_question"] = match
                    aliases.append("parenting_data.dinner_questions[] -> days[].dinner_question")

    nutrition = data.get("nutrition_data")
    if isinstance(nutrition, dict):
        _set_if_absent(
            nutrition,
            "lunch_suggestions",
            nutrition.get("lunch_recommendations"),
            aliases,
            "nutrition_data.lunch_recommendations -> nutrition_data.lunch_suggestions",
        )
        _set_if_absent(
            nutrition,
            "snack_suggestions",
            nutrition.get("snack_recommendations"),
            aliases,
            "nutrition_data.snack_recommendations -> nutrition_data.snack_suggestions",
        )
        if not data.get("nutrition_summary"):
            summary = nutrition.get("weekly_nutrition_summary") or nutrition.get("weekly_summary")
            if summary:
                data["nutrition_summary"] = summary
                aliases.append("nutrition_data.weekly_*summary -> nutrition_summary")

    newsletter = data.get("newsletter_data")
    if isinstance(newsletter, dict):
        newsletter.setdefault("clusters", [])
        if "newsletter_title" not in newsletter and newsletter.get("title"):
            newsletter["newsletter_title"] = newsletter["title"]
            aliases.append("newsletter_data.title -> newsletter_data.newsletter_title")

    deduped_aliases: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        if alias not in seen:
            deduped_aliases.append(alias)
            seen.add(alias)

    return data, deduped_aliases

