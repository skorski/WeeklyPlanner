#!/usr/bin/env python3
"""Fetch recent links from a Linkwarden instance and extract full article content."""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import urllib.request
import urllib.error
import urllib.parse

from dotenv import load_dotenv

# Load .env from skill directory
SKILL_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SKILL_DIR / ".env")

LINKWARDEN_URL = os.getenv("LINKWARDEN_URL", "").rstrip("/")
LINKWARDEN_TOKEN = os.getenv("LINKWARDEN_TOKEN", "")


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and return plain text with basic structure."""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True
        elif tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li"):
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li"):
            self._text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self):
        raw = "".join(self._text)
        # Collapse whitespace but preserve paragraph breaks
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html_content):
    """Convert HTML to readable plain text."""
    parser = HTMLTextExtractor()
    parser.feed(html_content)
    return parser.get_text()


def api_request(path, accept="application/json"):
    """Make an authenticated request to the Linkwarden API."""
    url = f"{LINKWARDEN_URL}{path}"
    headers = {
        "Authorization": f"Bearer {LINKWARDEN_TOKEN}",
        "Accept": accept,
        "User-Agent": "WeeklyPlannerLinkwardenSkill/1.0",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            if "json" in content_type or "json" in accept:
                return json.loads(data.decode("utf-8"))
            return data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"API error {e.code} for {path}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Request failed for {path}: {e}", file=sys.stderr)
        return None


def fetch_links(days=7):
    """Fetch all links, filtered to the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_links = []
    cursor = 0

    while True:
        # Use the /api/v1/links endpoint (still functional)
        path = f"/api/v1/links?sort=0&cursor={cursor}"
        data = api_request(path)

        if not data or not isinstance(data, dict):
            break

        response_links = data.get("response", [])
        if not response_links:
            break

        for link in response_links:
            created = link.get("createdAt", "")
            try:
                link_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if link_date >= cutoff:
                all_links.append(link)
            else:
                # Links are sorted newest-first; once we pass cutoff, stop
                return all_links

        cursor += len(response_links)

    return all_links


def fetch_readable_archive(link_id):
    """Fetch the readable (readability) archive for a link. Format 3 = readability."""
    path = f"/api/v1/archives/{link_id}?format=3"
    data = api_request(path, accept="*/*")

    if data is None:
        return None

    # The readable archive may be JSON with content or raw HTML
    if isinstance(data, str):
        # Could be HTML or JSON string
        try:
            parsed = json.loads(data)
            # Readability JSON has a "content" field with HTML
            if isinstance(parsed, dict) and "content" in parsed:
                return {
                    "title": parsed.get("title", ""),
                    "content": html_to_text(parsed["content"]),
                    "html_content": parsed["content"],
                    "excerpt": parsed.get("excerpt", ""),
                }
            return None
        except (json.JSONDecodeError, ValueError):
            # Raw HTML
            return {
                "title": "",
                "content": html_to_text(data),
                "html_content": data,
                "excerpt": "",
            }
    elif isinstance(data, dict):
        if "content" in data:
            return {
                "title": data.get("title", ""),
                "content": html_to_text(data["content"]),
                "html_content": data["content"],
                "excerpt": data.get("excerpt", ""),
            }

    return None


def fetch_monolith_archive(link_id):
    """Fetch the monolith HTML archive for a link. Format 4 = monolith."""
    path = f"/api/v1/archives/{link_id}?format=4"
    data = api_request(path, accept="*/*")

    if data and isinstance(data, str) and len(data) > 100:
        return {
            "content": html_to_text(data),
            "html_content": data,
        }
    return None


def extract_article_content(link):
    """Extract full article content from a link, trying multiple sources.

    Priority:
    1. Readable archive (format=3) — clean extracted article
    2. Monolith archive (format=4) — full saved HTML page
    3. textContent field — Linkwarden's built-in text extraction
    4. description field — user-provided or auto-extracted summary
    """
    link_id = link.get("id")

    # 1. Try readable archive
    readable = fetch_readable_archive(link_id)
    if readable and len(readable.get("content", "")) > 100:
        return {
            "source": "readable_archive",
            "text": readable["content"],
            "html": readable.get("html_content", ""),
            "excerpt": readable.get("excerpt", ""),
        }

    # 2. Try monolith archive
    monolith = fetch_monolith_archive(link_id)
    if monolith and len(monolith.get("content", "")) > 100:
        return {
            "source": "monolith_archive",
            "text": monolith["content"],
            "html": monolith.get("html_content", ""),
            "excerpt": "",
        }

    # 3. Use textContent from the link object
    text_content = link.get("textContent", "")
    if text_content and len(text_content) > 50:
        return {
            "source": "text_content",
            "text": text_content,
            "html": "",
            "excerpt": "",
        }

    # 4. Fall back to description
    description = link.get("description", "")
    return {
        "source": "description_only",
        "text": description,
        "html": "",
        "excerpt": description,
    }


def process_links(links):
    """Process raw link objects into structured article data."""
    articles = []

    for i, link in enumerate(links):
        link_id = link.get("id", "")
        name = link.get("name", "Untitled")
        url = link.get("url", "")
        description = link.get("description", "")
        created = link.get("createdAt", "")
        tags = [t.get("name", "") for t in link.get("tags", []) if isinstance(t, dict)]
        collection = link.get("collection", {})
        collection_name = collection.get("name", "") if isinstance(collection, dict) else ""

        print(f"  [{i+1}/{len(links)}] Fetching content: {name[:60]}...", file=sys.stderr)

        # Extract full content
        content = extract_article_content(link)

        article = {
            "id": link_id,
            "title": name,
            "url": url,
            "description": description,
            "created_at": created,
            "tags": tags,
            "collection": collection_name,
            "content_source": content["source"],
            "full_text": content["text"],
            "excerpt": content.get("excerpt", description),
            "word_count": len(content["text"].split()) if content["text"] else 0,
        }

        articles.append(article)

    return articles


def main():
    parser = argparse.ArgumentParser(
        description="Fetch recent links from Linkwarden and extract article content"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: stdout)",
    )
    parser.add_argument(
        "--skip-archives",
        action="store_true",
        help="Skip fetching archive content (use textContent only)",
    )
    args = parser.parse_args()

    if not LINKWARDEN_URL:
        print("Error: LINKWARDEN_URL not set in .env", file=sys.stderr)
        sys.exit(1)
    if not LINKWARDEN_TOKEN:
        print("Error: LINKWARDEN_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching links from {LINKWARDEN_URL} (last {args.days} days)...", file=sys.stderr)

    # Fetch links
    links = fetch_links(days=args.days)
    print(f"Found {len(links)} links from the last {args.days} days", file=sys.stderr)

    if not links:
        # Output empty array
        result = {"articles": [], "fetched_at": datetime.now(timezone.utc).isoformat(), "days": args.days}
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Empty result written to {args.output}", file=sys.stderr)
        else:
            print(output)
        sys.exit(0)

    # Process and extract content
    print("Extracting article content...", file=sys.stderr)
    articles = process_links(links)

    # Build result
    result = {
        "articles": articles,
        "total": len(articles),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "days": args.days,
        "source_url": LINKWARDEN_URL,
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {len(articles)} articles to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Print summary
    sources = {}
    for a in articles:
        src = a["content_source"]
        sources[src] = sources.get(src, 0) + 1
    print("\nContent sources:", file=sys.stderr)
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}", file=sys.stderr)

    total_words = sum(a["word_count"] for a in articles)
    print(f"Total words extracted: {total_words:,}", file=sys.stderr)


if __name__ == "__main__":
    main()
