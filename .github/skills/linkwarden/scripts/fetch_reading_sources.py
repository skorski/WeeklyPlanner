#!/usr/bin/env python3
"""Fetch weekly reading sources from Linkwarden, direct URLs, RSS feeds, and topics.

The output is a normalized source inventory for the newsletter skill. It does not
bypass authentication or paywalls: inaccessible pages are recorded in the
ingestion report so the user can provide text or rely on archived Linkwarden
copies.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


USER_AGENT = "WeeklyPlannerReadingSources/1.0"


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header", "noscript"):
            self._skip = True
        elif tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li"):
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "noscript"):
            self._skip = False
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li"):
            self._text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        raw = unescape("".join(self._text))
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def extract_title(html: str, fallback: str) -> str:
    for pattern in (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']title["\'][^>]+content=["\']([^"\']+)["\']',
        r"<title[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return unescape(re.sub(r"\s+", " ", match.group(1)).strip())
    return fallback


def fetch_url(url: str, timeout: int = 30) -> tuple[int, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()
    charset_match = re.search(r"charset=([^;]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1).strip() if charset_match else "utf-8"
    return status, content_type, data.decode(charset, errors="replace")


def normalize_direct_url(url: str) -> tuple[dict, dict]:
    base = {
        "type": "url",
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        status, content_type, body = fetch_url(url)
        text = html_to_text(body) if "html" in content_type.lower() or "<html" in body[:500].lower() else body.strip()
        title = extract_title(body, url)
        word_count = len(text.split())
        source = {
            **base,
            "status": "ok" if word_count >= 50 else "thin_content",
            "http_status": status,
            "content_type": content_type,
            "title": title,
            "full_text": text,
            "word_count": word_count,
            "content_source": "direct_url",
        }
        report = {
            "type": "url",
            "url": url,
            "status": source["status"],
            "word_count": word_count,
            "message": "Fetched directly" if word_count >= 50 else "Fetched, but extracted text is short",
        }
        return source, report
    except urllib.error.HTTPError as exc:
        return {
            **base,
            "status": "failed",
            "title": url,
            "full_text": "",
            "word_count": 0,
            "content_source": "direct_url",
            "failure_reason": f"HTTP {exc.code}: {exc.reason}",
        }, {
            "type": "url",
            "url": url,
            "status": "failed",
            "message": f"HTTP {exc.code}: {exc.reason}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            **base,
            "status": "failed",
            "title": url,
            "full_text": "",
            "word_count": 0,
            "content_source": "direct_url",
            "failure_reason": str(exc),
        }, {
            "type": "url",
            "url": url,
            "status": "failed",
            "message": str(exc),
        }


def text_of(element, names: tuple[str, ...]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def link_of(element) -> str:
    link = text_of(element, ("link",))
    if link:
        return link
    for candidate in element.findall("{http://www.w3.org/2005/Atom}link"):
        href = candidate.attrib.get("href")
        if href:
            return href
    return ""


def parse_feed(feed_url: str, max_items: int) -> tuple[list[dict], dict]:
    try:
        _status, _content_type, body = fetch_url(feed_url)
        root = ET.fromstring(body)
    except Exception as exc:
        return [], {
            "type": "rss",
            "url": feed_url,
            "status": "failed",
            "message": str(exc),
        }

    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    records = []
    for item in items[:max_items]:
        title = text_of(item, ("title", "{http://www.w3.org/2005/Atom}title")) or "Untitled feed item"
        url = link_of(item)
        published = text_of(item, ("pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"))
        summary = text_of(item, ("description", "summary", "{http://www.w3.org/2005/Atom}summary"))
        records.append({
            "type": "rss_item",
            "feed_url": feed_url,
            "url": url,
            "title": unescape(title),
            "published_at": published,
            "description": html_to_text(summary) if summary else "",
            "status": "pending_fetch" if url else "no_link",
        })

    return records, {
        "type": "rss",
        "url": feed_url,
        "status": "ok",
        "items_found": len(items),
        "items_selected": len(records),
    }


def fetch_linkwarden(days: int) -> tuple[list[dict], dict]:
    script = Path(__file__).resolve().with_name("fetch_links.py")
    with tempfile.TemporaryDirectory(prefix="weekly-linkwarden-") as tmp:
        output = Path(tmp) / "links.json"
        proc = subprocess.run(
            [sys.executable, str(script), "--days", str(days), "-o", str(output)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not output.exists():
            return [], {
                "type": "linkwarden",
                "status": "failed",
                "message": (proc.stderr or proc.stdout).strip(),
            }
        payload = json.loads(output.read_text(encoding="utf-8"))

    articles = []
    for article in payload.get("articles", []):
        articles.append({
            "type": "linkwarden",
            "status": "ok",
            "url": article.get("url", ""),
            "title": article.get("title", "Untitled"),
            "tags": article.get("tags", []),
            "collection": article.get("collection", ""),
            "created_at": article.get("created_at", ""),
            "full_text": article.get("full_text", ""),
            "word_count": article.get("word_count", 0),
            "content_source": f"linkwarden:{article.get('content_source', '')}",
        })
    return articles, {
        "type": "linkwarden",
        "status": "ok",
        "days": days,
        "items_selected": len(articles),
    }


def load_request(path: Path | None) -> dict:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return payload.get("weekly_read", payload)


def split_values(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for part in value.split(","):
            stripped = part.strip()
            if stripped:
                result.append(stripped)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and normalize weekly reading sources")
    parser.add_argument("--input", help="JSON request file; may contain a weekly_read object")
    parser.add_argument("--urls", action="append", help="Comma-separated URL(s) to fetch")
    parser.add_argument("--rss-feeds", action="append", help="Comma-separated RSS/Atom feed URL(s)")
    parser.add_argument("--required-topics", action="append", help="Comma-separated research topic(s)")
    parser.add_argument("--include-linkwarden", action="store_true")
    parser.add_argument("--linkwarden-days", type=int, default=7)
    parser.add_argument("--rss-max-items", type=int, default=5)
    parser.add_argument("--no-fetch-rss-items", action="store_true")
    parser.add_argument("-o", "--output", default="reading_sources.json")
    parser.add_argument("--report", default="reading_ingestion_report.json")
    args = parser.parse_args()

    request = load_request(Path(args.input) if args.input else None)
    urls = list(request.get("urls") or []) + split_values(args.urls)
    rss_feeds = list(request.get("rss_feeds") or []) + split_values(args.rss_feeds)
    topics = list(request.get("required_topics") or []) + split_values(args.required_topics)
    include_linkwarden = bool(request.get("include_linkwarden", False) or args.include_linkwarden)
    linkwarden_days = int(request.get("linkwarden_days", args.linkwarden_days))

    sources = []
    reports = []

    if include_linkwarden:
        records, report = fetch_linkwarden(linkwarden_days)
        sources.extend(records)
        reports.append(report)

    for url in urls:
        source, report = normalize_direct_url(url)
        sources.append(source)
        reports.append(report)

    for feed_url in rss_feeds:
        feed_items, report = parse_feed(feed_url, args.rss_max_items)
        reports.append(report)
        for item in feed_items:
            if item.get("url") and not args.no_fetch_rss_items:
                source, fetch_report = normalize_direct_url(item["url"])
                source.update({
                    "type": "rss_item",
                    "feed_url": feed_url,
                    "published_at": item.get("published_at", ""),
                })
                sources.append(source)
                reports.append(fetch_report | {"feed_url": feed_url})
            else:
                sources.append(item)

    for topic in topics:
        sources.append({
            "type": "topic",
            "status": "needs_research",
            "title": topic,
            "url": "",
            "full_text": "",
            "word_count": 0,
            "content_source": "user_required_topic",
        })
        reports.append({
            "type": "topic",
            "topic": topic,
            "status": "needs_research",
            "message": "Topic should be covered by newsletter research.",
        })

    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "include_linkwarden": include_linkwarden,
            "linkwarden_days": linkwarden_days,
            "urls": urls,
            "rss_feeds": rss_feeds,
            "required_topics": topics,
        },
        "sources": sources,
        "articles": [s for s in sources if s.get("type") != "topic"],
        "topics": [s for s in sources if s.get("type") == "topic"],
        "summary": {
            "total_sources": len(sources),
            "successful_sources": sum(1 for s in sources if s.get("status") in ("ok", "thin_content")),
            "failed_sources": sum(1 for s in sources if s.get("status") == "failed"),
            "topics": len(topics),
            "total_words": sum(int(s.get("word_count") or 0) for s in sources),
        },
    }
    report_payload = {
        "schema_version": "1.0",
        "generated_at": payload["generated_at"],
        "status": "PASS" if not any(r.get("status") == "failed" for r in reports) else "WARN",
        "reports": reports,
        "summary": payload["summary"],
    }

    output_path = Path(args.output)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"READING_SOURCES={output_path}", file=sys.stderr)
    print(f"READING_INGESTION_REPORT={report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
