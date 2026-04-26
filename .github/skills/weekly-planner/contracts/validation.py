from __future__ import annotations

from datetime import datetime
from typing import Any

from .registry import normalize_text, path_count, resolve_path
from .section_manifest import build_section_manifest, manifest_failures


DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def issue(severity: str, check: str, path: str, message: str) -> dict[str, str]:
    return {
        "severity": severity,
        "check": check,
        "path": path,
        "message": message,
    }


def _day_name(day: dict[str, Any]) -> str:
    return (day.get("day_of_week") or day.get("long_name") or day.get("name") or "").split(",")[0].strip().lower()


def _validate_days(plan_data: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    days = plan_data.get("days", [])
    if not isinstance(days, list):
        return [issue("error", "days_shape", "days", "days must be an array")]
    if len(days) != 7:
        issues.append(issue("error", "days_count", "days", f"expected 7 days, found {len(days)}"))

    for i, day in enumerate(days):
        if not isinstance(day, dict):
            issues.append(issue("error", "day_shape", f"days[{i}]", "day must be an object"))
            continue
        for field in ("dinner", "album"):
            if not str(day.get(field, "")).strip():
                issues.append(issue("error", f"day_{field}", f"days[{i}].{field}", f"{field} is required"))
        rc = day.get("recipe_card")
        if not isinstance(rc, dict):
            issues.append(issue("error", "recipe_card", f"days[{i}].recipe_card", "recipe_card must be present as an object"))
        elif not rc.get("nonna_says"):
            issues.append(issue("error", "recipe_card_nonna", f"days[{i}].recipe_card.nonna_says", "recipe_card.nonna_says is required"))
        dq = day.get("dinner_question")
        if not isinstance(dq, dict) or not dq.get("question"):
            issues.append(issue("error", "dinner_question", f"days[{i}].dinner_question", "dinner_question.question is required"))

    return issues


def _validate_parenting(plan_data: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    parenting = plan_data.get("parenting_data")
    if not isinstance(parenting, dict):
        return [issue("error", "parenting_presence", "parenting_data", "parenting_data is required")]
    questions = parenting.get("dinner_questions", [])
    nudges = parenting.get("nudges", [])
    if not isinstance(parenting.get("weekly_theme"), dict) or not parenting["weekly_theme"].get("title"):
        issues.append(issue("error", "parenting_theme", "parenting_data.weekly_theme", "weekly_theme.title is required"))
    if not isinstance(questions, list) or len(questions) != 7:
        issues.append(issue("error", "parenting_questions", "parenting_data.dinner_questions", f"expected 7 dinner questions, found {len(questions) if isinstance(questions, list) else 0}"))
    if not isinstance(nudges, list) or len(nudges) < 3:
        issues.append(issue("error", "parenting_nudges", "parenting_data.nudges", f"expected at least 3 nudges, found {len(nudges) if isinstance(nudges, list) else 0}"))
    for i, nudge in enumerate(nudges if isinstance(nudges, list) else []):
        if not isinstance(nudge, dict):
            issues.append(issue("error", "parenting_nudge_shape", f"parenting_data.nudges[{i}]", "nudge must be an object"))
            continue
        how_to = nudge.get("how_to", [])
        if not isinstance(how_to, list) or len(how_to) < 3:
            issues.append(issue("warning", "parenting_nudge_depth", f"parenting_data.nudges[{i}].how_to", "nudge should include at least 3 concrete steps"))
        context_words = _word_count(nudge.get("context", ""))
        suggestion_words = _word_count(nudge.get("suggestion", ""))
        if context_words < 25 or suggestion_words < 25:
            issues.append(issue("warning", "parenting_nudge_copy_depth", f"parenting_data.nudges[{i}]", "nudge context and suggestion should be substantive enough for family-coaching depth"))
    return issues


def _validate_stoic(plan_data: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    stoic = plan_data.get("stoic_data")
    if not isinstance(stoic, dict):
        return [issue("error", "stoic_presence", "stoic_data", "stoic_data is required")]
    meditations = stoic.get("meditations", [])
    if not isinstance(stoic.get("theme"), dict) or not stoic["theme"].get("title"):
        issues.append(issue("error", "stoic_theme", "stoic_data.theme", "theme.title is required"))
    if not isinstance(stoic.get("anchor_quote"), dict) or not stoic["anchor_quote"].get("text"):
        issues.append(issue("error", "stoic_anchor_quote", "stoic_data.anchor_quote", "anchor_quote.text is required"))
    if not isinstance(meditations, list) or len(meditations) != 7:
        issues.append(issue("error", "stoic_meditations", "stoic_data.meditations", f"expected 7 daily meditations, found {len(meditations) if isinstance(meditations, list) else 0}"))
    else:
        meditation_days = {
            str(m.get("day", "")).strip().lower()
            for m in meditations
            if isinstance(m, dict)
        }
        for day in DAYS:
            if day not in meditation_days:
                issues.append(issue("error", "stoic_meditation_day", "stoic_data.meditations", f"missing {day.title()} meditation"))
    return issues


def _validate_principles(plan_data: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    principles = plan_data.get("principles_data")
    if not isinstance(principles, dict):
        return [issue("error", "principles_presence", "principles_data", "principles_data is required")]
    entries = principles.get("daily_entries", [])
    if not isinstance(entries, list) or len(entries) != 7:
        issues.append(issue("error", "principles_entries", "principles_data.daily_entries", f"expected 7 entries, found {len(entries) if isinstance(entries, list) else 0}"))
    for i, entry in enumerate(entries if isinstance(entries, list) else []):
        essay = entry.get("essay", "") if isinstance(entry, dict) else ""
        if "\n\n" not in essay:
            issues.append(issue("warning", "principles_essay_paragraphs", f"principles_data.daily_entries[{i}].essay", "essay should contain two paragraphs separated by a blank line"))
    return issues


def _url_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text[:-1] if text.endswith("/") else text


def _word_count(value: Any) -> int:
    return len(str(value or "").split())


def _resolve_sequence(data: Any, path: str) -> list[Any]:
    values = resolve_path(data, path)
    if len(values) == 1 and isinstance(values[0], list):
        return values[0]
    return values


def _validate_weekly_read(
    plan_data: dict[str, Any],
    run_request: dict[str, Any] | None,
    reading_sources: dict[str, Any] | None,
) -> list[dict[str, str]]:
    issues = []
    newsletter = plan_data.get("newsletter_data")
    requested_urls = path_count(run_request or {}, "weekly_read.urls")
    requested_topics = path_count(run_request or {}, "weekly_read.required_topics")
    if requested_urls or requested_topics or newsletter or reading_sources:
        clusters = newsletter.get("clusters", []) if isinstance(newsletter, dict) else []
        if not clusters:
            issues.append(issue("error", "weekly_read_clusters", "newsletter_data.clusters", "weekly read requires at least one cluster when sources or topics are present"))
        for i, cluster in enumerate(clusters if isinstance(clusters, list) else []):
            if not isinstance(cluster, dict):
                continue
            synthesis_words = _word_count(cluster.get("synthesis", ""))
            if synthesis_words < 500 or synthesis_words > 1000:
                issues.append(issue(
                    "error",
                    "weekly_read_synthesis_length",
                    f"newsletter_data.clusters[{i}].synthesis",
                    f"cluster synthesis must be a 500-1000 word essay; found {synthesis_words} words",
                ))
        if reading_sources:
            sources = reading_sources.get("sources", [])
            source_urls = {_url_key(s.get("url")) for s in sources if isinstance(s, dict) and s.get("url")}
            for url in _resolve_sequence(run_request or {}, "weekly_read.urls"):
                if _url_key(url) not in source_urls:
                    issues.append(issue("error", "weekly_read_requested_url", "reading_sources.sources", f"requested URL was not ingested: {url}"))

            cluster_urls = {
                _url_key(article.get("url"))
                for cluster in clusters if isinstance(cluster, dict)
                for article in cluster.get("articles", []) if isinstance(article, dict) and article.get("url")
            }
            unused_urls = {
                _url_key(source.get("url"))
                for source in (newsletter.get("not_used_sources", []) if isinstance(newsletter, dict) else [])
                if isinstance(source, dict) and source.get("url")
            }
            for source in sources:
                if not isinstance(source, dict):
                    continue
                if source.get("type") == "topic":
                    continue
                if source.get("status") not in ("ok", "thin_content"):
                    continue
                source_url = _url_key(source.get("url"))
                if source_url and source_url not in cluster_urls and source_url not in unused_urls:
                    issues.append(issue("warning", "weekly_read_unused_source", "newsletter_data.clusters[].articles", f"ingested source is not referenced by the newsletter: {source.get('url')}"))

            newsletter_text = normalize_text(" ".join(
                str(part)
                for part in (
                    [newsletter.get("reflections", "")] if isinstance(newsletter, dict) else []
                ) + [
                    value
                    for cluster in clusters if isinstance(cluster, dict)
                    for value in (cluster.get("theme", ""), cluster.get("synthesis", ""))
                ]
            ))
            topic_values = list(_resolve_sequence(run_request or {}, "weekly_read.required_topics"))
            topic_values.extend(
                source.get("title")
                for source in sources
                if isinstance(source, dict) and source.get("type") == "topic"
            )
            for topic in topic_values:
                topic_norm = normalize_text(topic)
                key_terms = [word for word in topic_norm.split() if len(word) >= 5][:2]
                if key_terms and not any(term in newsletter_text for term in key_terms):
                    issues.append(issue("warning", "weekly_read_topic_coverage", "newsletter_data.clusters", f"required topic may not be covered explicitly: {topic}"))
    return issues


def _requested_news_source_url(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("feed_url") or raw.get("url") or ""
    return ""


def _validate_news_feed(
    plan_data: dict[str, Any],
    run_request: dict[str, Any] | None,
) -> list[dict[str, str]]:
    issues = []
    requested_sources = []
    if isinstance(run_request, dict):
        news_request = run_request.get("news_feed")
        if isinstance(news_request, dict):
            requested_sources = news_request.get("sources", []) or []

    news_feed = plan_data.get("news_feed_data")
    if requested_sources or news_feed:
        if not isinstance(news_feed, dict):
            return [issue("error", "news_feed_presence", "news_feed_data", "news_feed_data is required when news_feed.sources are requested")]

        sources = news_feed.get("sources", [])
        articles = news_feed.get("articles", [])
        if not isinstance(sources, list) or not sources:
            issues.append(issue("error", "news_feed_sources", "news_feed_data.sources", "news feed requires source metadata"))
        if not isinstance(articles, list):
            issues.append(issue("error", "news_feed_articles_shape", "news_feed_data.articles", "articles must be an array"))
            articles = []

        source_urls = {
            _url_key(source.get("url") or source.get("feed_url"))
            for source in sources
            if isinstance(source, dict)
        }
        source_urls.update(
            _url_key(source.get("feed_url"))
            for source in sources
            if isinstance(source, dict) and source.get("feed_url")
        )
        for raw in requested_sources:
            requested_url = _requested_news_source_url(raw)
            if requested_url and _url_key(requested_url) not in source_urls:
                issues.append(issue("error", "news_feed_requested_source", "news_feed_data.sources", f"requested news source was not represented: {requested_url}"))

        for i, source in enumerate(sources if isinstance(sources, list) else []):
            if not isinstance(source, dict):
                issues.append(issue("error", "news_feed_source_shape", f"news_feed_data.sources[{i}]", "source must be an object"))
                continue
            if source.get("status") not in (None, "", "ok"):
                issues.append(issue("warning", "news_feed_source_status", f"news_feed_data.sources[{i}].status", f"news source did not fetch cleanly: {source.get('name') or source.get('url')}"))

        for i, article in enumerate(articles):
            if not isinstance(article, dict):
                issues.append(issue("error", "news_feed_article_shape", f"news_feed_data.articles[{i}]", "article must be an object"))
                continue
            for field in ("source_name", "title", "url"):
                if not str(article.get(field, "")).strip():
                    issues.append(issue("error", f"news_feed_article_{field}", f"news_feed_data.articles[{i}].{field}", f"{field} is required"))
            if article.get("status") in (None, "", "ok") and not str(article.get("full_text", "")).strip():
                issues.append(issue("error", "news_feed_article_text", f"news_feed_data.articles[{i}].full_text", "full_text is required for fetched news articles"))

        total_articles = news_feed.get("total_articles")
        if not isinstance(total_articles, int):
            issues.append(issue("error", "news_feed_total_articles", "news_feed_data.total_articles", "total_articles must be an integer"))
        elif total_articles != len(articles):
            issues.append(issue("warning", "news_feed_total_articles_mismatch", "news_feed_data.total_articles", f"total_articles is {total_articles}, but articles has {len(articles)} items"))

    return issues


def _validate_history_duplicates(plan_data: dict[str, Any], history: dict[str, Any] | None) -> list[dict[str, str]]:
    if not history:
        return []
    issues = []
    checks = [
        ("parenting theme", "parenting_data.weekly_theme.title", history.get("parenting_themes", [])),
        ("stoic theme", "stoic_data.theme.title", history.get("stoic_themes", [])),
        ("principles theme", "principles_data.theme.title", history.get("principles_themes", [])),
    ]
    for label, path, previous in checks:
        current_values = [normalize_text(v) for v in resolve_path(plan_data, path)]
        previous_values = {normalize_text(v) for v in previous}
        for value in current_values:
            if value and value in previous_values:
                issues.append(issue("warning", "history_duplicate", path, f"{label} repeats recent history: {value}"))
    return issues


def validate_plan_data(
    plan_data: dict[str, Any],
    registry: dict[str, Any],
    *,
    run_request: dict[str, Any] | None = None,
    history: dict[str, Any] | None = None,
    reading_sources: dict[str, Any] | None = None,
    aliases_applied: list[str] | None = None,
) -> dict[str, Any]:
    manifest = build_section_manifest(
        plan_data,
        registry,
        run_request=run_request,
        aliases_applied=aliases_applied,
    )
    issues: list[dict[str, str]] = []
    for failure in manifest_failures(manifest):
        issues.append(issue("error", "section_manifest", "section_manifest", failure))

    issues.extend(_validate_days(plan_data))
    issues.extend(_validate_parenting(plan_data))
    issues.extend(_validate_stoic(plan_data))
    issues.extend(_validate_principles(plan_data))
    issues.extend(_validate_weekly_read(plan_data, run_request, reading_sources))
    issues.extend(_validate_news_feed(plan_data, run_request))
    issues.extend(_validate_history_duplicates(plan_data, history))

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    return {
        "status": "FAIL" if errors else "PASS",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": issues,
        "aliases_applied": aliases_applied or [],
        "section_manifest": manifest,
    }

