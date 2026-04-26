#!/usr/bin/env python3
"""Fetch recent news articles and write a parseable markdown artifact.

The markdown file is the source of truth for weekly-planner ingestion. It keeps
human-readable article text while embedding small JSON metadata blocks that the
assembler can parse deterministically.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


USER_AGENT = "WeeklyPlannerNewsFeed/1.0"
MIN_OK_WORDS = 80


class HTMLTextExtractor(HTMLParser):
    """Small HTML-to-text extractor for article pages."""

    BLOCK_TAGS = {"p", "br", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "blockquote"}
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg", "aside", "form"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")
        if tag == "li":
            self._parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def get_text(self) -> str:
        text = unescape("".join(self._parts))
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    body: str


def fetch_url(url: str, timeout: int = 30) -> FetchResult:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read()
        final_url = response.geturl()
        status = getattr(response, "status", 200)
    charset_match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1).strip() if charset_match else "utf-8"
    return FetchResult(url, final_url, status, content_type, data.decode(charset, errors="replace"))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    children = list(element)
    for name in names:
        for child in children:
            if local_name(child.tag) == name:
                return "".join(child.itertext()).strip()
    return ""


def child_link(element: ET.Element) -> str:
    for child in list(element):
        if local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href.strip()
        if child.text:
            return child.text.strip()
    return ""


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass

    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def parse_date_boundary(value: str | None, *, end: bool = False) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        date = datetime.strptime(raw, "%Y-%m-%d").date()
        if end:
            return datetime.combine(date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return datetime.combine(date, time.min, tzinfo=timezone.utc)
    return parse_datetime(raw)


def in_window(published: datetime | None, start_at: datetime, end_at: datetime, include_undated: bool) -> bool:
    if published is None:
        return include_undated
    return start_at <= published < end_at


def html_to_text(html: str) -> str:
    article_match = re.search(r"<article\b[^>]*>(.*?)</article>", html, re.IGNORECASE | re.DOTALL)
    if article_match:
        html = article_match.group(1)
    else:
        main_match = re.search(r"<main\b[^>]*>(.*?)</main>", html, re.IGNORECASE | re.DOTALL)
        if main_match:
            html = main_match.group(1)
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def extract_meta(html: str, names: tuple[str, ...]) -> str:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return unescape(re.sub(r"\s+", " ", match.group(1)).strip())
    return ""


def extract_title(html: str, fallback: str) -> str:
    title = extract_meta(html, ("og:title", "twitter:title", "title"))
    if title:
        return title
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return unescape(re.sub(r"\s+", " ", match.group(1)).strip())
    return fallback


def extract_published(html: str) -> str:
    return extract_meta(
        html,
        (
            "article:published_time",
            "article:modified_time",
            "datePublished",
            "date",
            "pubdate",
        ),
    )


def summarize(text: str, max_words: int = 55) -> str:
    words = text.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "..."


def discover_feed_url(source_url: str) -> tuple[str | None, dict[str, Any]]:
    parsed = urllib.parse.urlparse(source_url)
    if parsed.path.lower().endswith((".xml", ".rss", ".atom")) or "/feed" in parsed.path.lower():
        return source_url, {"status": "ok", "method": "provided_feed"}

    try:
        result = fetch_url(source_url)
    except Exception as exc:
        return None, {"status": "failed", "method": "homepage", "message": str(exc)}

    body = result.body
    link_pattern = re.compile(r"<link\b([^>]+)>", re.IGNORECASE)
    for match in link_pattern.finditer(body):
        attrs = match.group(1)
        if "alternate" not in attrs.lower():
            continue
        if "rss" not in attrs.lower() and "atom" not in attrs.lower():
            continue
        href_match = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if href_match:
            return urllib.parse.urljoin(result.final_url, href_match.group(1)), {
                "status": "ok",
                "method": "html_alternate",
            }

    fallback = urllib.parse.urljoin(result.final_url.rstrip("/") + "/", "feed/")
    try:
        feed_result = fetch_url(fallback)
        if "<rss" in feed_result.body[:500].lower() or "<feed" in feed_result.body[:500].lower():
            return fallback, {"status": "ok", "method": "slash_feed"}
    except Exception as exc:
        return None, {"status": "failed", "method": "slash_feed", "message": str(exc)}

    return None, {"status": "failed", "method": "discovery", "message": "No RSS/Atom feed discovered"}


def parse_feed_items(feed_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        result = fetch_url(feed_url)
        root = ET.fromstring(result.body)
    except Exception as exc:
        return [], {"url": feed_url, "status": "failed", "message": str(exc)}

    items = [item for item in root.iter() if local_name(item.tag) in {"item", "entry"}]
    records: list[dict[str, Any]] = []
    for item in items:
        title = child_text(item, ("title",)) or "Untitled"
        url = child_link(item)
        published = child_text(item, ("pubdate", "published", "updated", "date"))
        feed_text = child_text(item, ("encoded", "content", "description", "summary"))
        records.append(
            {
                "title": unescape(re.sub(r"\s+", " ", title).strip()),
                "url": url,
                "published_at": published,
                "feed_text": html_to_text(feed_text) if feed_text else "",
            }
        )

    return records, {
        "url": feed_url,
        "status": "ok",
        "items_found": len(items),
    }


def normalize_source(raw: Any, index: int) -> dict[str, str]:
    if isinstance(raw, str):
        url = raw.strip()
        return {"name": source_name_from_url(url, index), "url": url}
    if not isinstance(raw, dict):
        raise ValueError(f"news_feed.sources[{index}] must be a URL string or object")
    url = (raw.get("feed_url") or raw.get("url") or "").strip()
    if not url:
        raise ValueError(f"news_feed.sources[{index}] is missing url or feed_url")
    name = (raw.get("name") or source_name_from_url(url, index)).strip()
    normalized = {"name": name, "url": url}
    if raw.get("feed_url"):
        normalized["feed_url"] = raw["feed_url"].strip()
    return normalized


def source_name_from_url(url: str, index: int) -> str:
    host = urllib.parse.urlparse(url).netloc
    return host or f"Source {index + 1}"


def load_request(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return payload.get("news_feed", payload)


def split_values(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for part in value.split(","):
            stripped = part.strip()
            if stripped:
                result.append(stripped)
    return result


def parse_cli_sources(values: list[str] | None) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for value in values or []:
        for part in value.split(","):
            item = part.strip()
            if not item:
                continue
            if "=" in item:
                name, url = item.split("=", 1)
                sources.append({"name": name.strip(), "url": url.strip()})
            else:
                sources.append({"name": source_name_from_url(item, len(sources)), "url": item})
    return sources


def fetch_article_text(item: dict[str, Any], fetch_article: bool) -> dict[str, Any]:
    feed_text = item.get("feed_text", "")
    if not item.get("url"):
        text = feed_text
        return {
            "status": "failed",
            "title": item.get("title", "Untitled"),
            "url": "",
            "published_at": item.get("published_at", ""),
            "full_text": text,
            "word_count": len(text.split()),
            "content_source": "feed:no_link",
            "summary": summarize(text),
            "failure_reason": "Feed item has no URL",
        }

    if not fetch_article:
        text = feed_text
        status = "ok" if len(text.split()) >= MIN_OK_WORDS else "thin_content"
        return {
            "status": status,
            "title": item.get("title", "Untitled"),
            "url": item["url"],
            "published_at": item.get("published_at", ""),
            "full_text": text,
            "word_count": len(text.split()),
            "content_source": "feed_text",
            "summary": summarize(text),
        }

    try:
        result = fetch_url(item["url"])
        article_text = html_to_text(result.body)
        title = extract_title(result.body, item.get("title", "Untitled"))
        published = item.get("published_at") or extract_published(result.body)
        if len(article_text.split()) < MIN_OK_WORDS and feed_text:
            text = feed_text
            content_source = "feed_text_fallback"
        else:
            text = article_text
            content_source = "article_html"
        word_count = len(text.split())
        return {
            "status": "ok" if word_count >= MIN_OK_WORDS else "thin_content",
            "title": title,
            "url": result.final_url,
            "published_at": published,
            "full_text": text,
            "word_count": word_count,
            "content_source": content_source,
            "summary": summarize(text),
        }
    except Exception as exc:
        text = feed_text
        word_count = len(text.split())
        return {
            "status": "thin_content" if text else "failed",
            "title": item.get("title", "Untitled"),
            "url": item["url"],
            "published_at": item.get("published_at", ""),
            "full_text": text,
            "word_count": word_count,
            "content_source": "feed_text_after_article_fetch_failed" if text else "article_fetch_failed",
            "summary": summarize(text),
            "failure_reason": str(exc),
        }


def json_comment(label: str, payload: dict[str, Any]) -> str:
    return f"<!-- {label}\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n-->"


def clean_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value or "Untitled").replace("#", "").strip()


def write_markdown(payload: dict[str, Any], output_path: Path) -> None:
    meta = {
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "start_date": payload["start_date"],
        "end_date": payload["end_date"],
        "source_count": payload["source_count"],
        "total_articles": payload["total_articles"],
        "sources": payload["sources"],
    }

    lines: list[str] = [
        "---",
        'news_feed_schema: "1.0"',
        f'generated_at: "{payload["generated_at"]}"',
        f'start_date: "{payload["start_date"]}"',
        f'end_date: "{payload["end_date"]}"',
        f"source_count: {payload['source_count']}",
        f"total_articles: {payload['total_articles']}",
        "---",
        "",
        "# News Feed",
        "",
        json_comment("news-feed-payload", meta),
        "",
        f"Window: {payload['start_date']} through {payload['end_date']}",
        "",
        "## Sources",
        "",
        "| Source | URL | Status | Selected |",
        "|---|---|---|---:|",
    ]

    for source in payload["sources"]:
        lines.append(
            f"| {source['name']} | {source['url']} | {source['status']} | {source.get('items_selected', 0)} |"
        )

    lines.extend(["", "## Articles", ""])
    if not payload["articles"]:
        lines.extend(["No articles matched the requested publication window.", ""])

    for index, article in enumerate(payload["articles"], start=1):
        metadata = {key: value for key, value in article.items() if key != "full_text"}
        lines.extend(
            [
                f"### Article {index}: {clean_heading(article.get('title', 'Untitled'))}",
                "",
                f"Source: {article.get('source_name', '')}",
                f"Published: {article.get('published_at', '') or 'unknown'}",
                f"URL: {article.get('url', '')}",
                "",
                json_comment("news-feed-item-start", metadata),
                "",
                article.get("full_text", "").strip() or "_No article text extracted._",
                "",
                "<!-- news-feed-item-end -->",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    request = load_request(Path(args.input) if args.input else None)
    raw_sources = list(request.get("sources") or [])
    raw_sources.extend(parse_cli_sources(args.source))
    raw_sources.extend({"name": source_name_from_url(url, len(raw_sources)), "url": url} for url in split_values(args.url))
    raw_sources.extend({"name": source_name_from_url(url, len(raw_sources)), "feed_url": url, "url": url} for url in split_values(args.rss_feed))

    sources = [normalize_source(raw, index) for index, raw in enumerate(raw_sources)]
    lookback_days = int(request.get("lookback_days", args.lookback_days))
    max_items = int(request.get("max_items_per_source", args.max_items_per_source))
    include_undated = bool(request.get("include_undated", args.include_undated))
    fetch_article = bool(request.get("fetch_article_text", not args.no_fetch_article_text))

    now = datetime.now(timezone.utc)
    start_at = parse_date_boundary(args.start or request.get("start_date")) or (now - timedelta(days=lookback_days))
    end_at = parse_date_boundary(args.end or request.get("end_date"), end=True) or now
    start_date = start_at.date().isoformat()
    end_date = (end_at - timedelta(microseconds=1)).date().isoformat()

    articles: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []

    for source in sources:
        source_url = source.get("feed_url") or source["url"]
        if source.get("feed_url"):
            feed_url, discovery = source_url, {"status": "ok", "method": "provided_feed"}
        else:
            feed_url, discovery = discover_feed_url(source_url)
        source_report: dict[str, Any] = {
            "name": source["name"],
            "url": source["url"],
            "feed_url": feed_url or "",
            "status": discovery.get("status", "failed"),
            "discovery": discovery,
            "items_found": 0,
            "items_selected": 0,
        }

        if not feed_url:
            source_report["message"] = discovery.get("message", "Feed discovery failed")
            source_reports.append(source_report)
            continue

        feed_items, feed_report = parse_feed_items(feed_url)
        source_report["status"] = feed_report.get("status", "failed")
        source_report["items_found"] = feed_report.get("items_found", 0)
        if source_report["status"] != "ok":
            source_report["message"] = feed_report.get("message", "Feed fetch failed")
            source_reports.append(source_report)
            continue

        selected: list[dict[str, Any]] = []
        for item in feed_items:
            published_dt = parse_datetime(item.get("published_at"))
            if in_window(published_dt, start_at, end_at, include_undated):
                selected.append(item)
            if len(selected) >= max_items:
                break

        for item in selected:
            article = fetch_article_text(item, fetch_article)
            article.update(
                {
                    "source_name": source["name"],
                    "source_url": source["url"],
                    "feed_url": feed_url,
                }
            )
            articles.append(article)

        source_report["items_selected"] = len(selected)
        source_reports.append(source_report)

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "start_date": start_date,
        "end_date": end_date,
        "source_count": len(sources),
        "total_articles": len(articles),
        "sources": source_reports,
        "articles": articles,
    }
    report = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "status": "PASS" if all(s["status"] == "ok" for s in source_reports) else "WARN",
        "summary": {
            "sources": len(source_reports),
            "articles": len(articles),
            "failed_sources": sum(1 for s in source_reports if s["status"] != "ok"),
            "total_words": sum(int(a.get("word_count") or 0) for a in articles),
        },
        "sources": source_reports,
        "articles": [
            {key: value for key, value in article.items() if key != "full_text"}
            for article in articles
        ],
    }
    return payload, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch recent news articles into parseable markdown")
    parser.add_argument("--input", help="JSON request file; may contain a news_feed object")
    parser.add_argument("--source", action="append", help="Source URL or Name=URL. May be comma-separated.")
    parser.add_argument("--url", action="append", help="Source homepage URL. May be comma-separated.")
    parser.add_argument("--rss-feed", action="append", help="RSS/Atom feed URL. May be comma-separated.")
    parser.add_argument("--start", help="Inclusive start date or datetime")
    parser.add_argument("--end", help="Inclusive end date or datetime")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--max-items-per-source", type=int, default=5)
    parser.add_argument("--include-undated", action="store_true")
    parser.add_argument("--no-fetch-article-text", action="store_true")
    parser.add_argument("-o", "--output", default="news-feed.md")
    parser.add_argument("--report", default="news_feed_report.json")
    args = parser.parse_args()

    try:
        payload, report = build_payload(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    output_path = Path(args.output)
    report_path = Path(args.report)
    write_markdown(payload, output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"NEWS_FEED_MARKDOWN={output_path}", file=sys.stderr)
    print(f"NEWS_FEED_REPORT={report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
