---
name: news-feed
description: Fetch recent articles from user-provided news sources, RSS/Atom feeds, or publication homepages; extract article text; write a parseable markdown file; and integrate the result into the weekly-planner workflow. Use when the user asks to add news sources, a news feed, current articles, Bellingcat-style source monitoring, or automatic article ingestion for the weekly plan.
---

# News Feed

Fetch recent articles from named sources and write a parseable markdown artifact
that the weekly planner can merge into `plan_data.json`.

## Workflow

1. Normalize requested sources from `weekly_plans/<YYYY-MM-DD>/week_request.json`.
2. Run the fetcher:

```bash
python .github/skills/news-feed/scripts/fetch_news_feed.py \
  --input weekly_plans/<YYYY-MM-DD>/week_request.json \
  -o weekly_plans/<YYYY-MM-DD>/news-feed.md \
  --report weekly_plans/<YYYY-MM-DD>/news_feed_report.json
```

3. Review `news_feed_report.json` for failed or thin extractions. Do not bypass
   paywalls or authentication. If a source is inaccessible, leave the failure in
   the report and ask the user for article text only if the missing source is
   essential.
4. Pass `news-feed.md` to the weekly-planner assembler:

```bash
python .github/skills/weekly-planner/scripts/assemble_plan.py \
  weekly_plans/<YYYY-MM-DD>/days.json \
  -o weekly_plans/<YYYY-MM-DD>/plan_data.json \
  --news-feed weekly_plans/<YYYY-MM-DD>/news-feed.md
```

When `--week-dir weekly_plans/<YYYY-MM-DD>` is used, the assembler auto-detects
`news-feed.md`.

## Input Contract

The request file may contain a top-level `news_feed` object:

```json
{
  "news_feed": {
    "lookback_days": 7,
    "max_items_per_source": 5,
    "sources": [
      {"name": "Bellingcat", "url": "https://www.bellingcat.com/"},
      {"name": "David Heinemeier Hansson", "feed_url": "https://world.hey.com/dhh/feed.atom"},
      {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index"},
      {"name": "Hacker News", "feed_url": "https://news.ycombinator.com/rss"},
      "https://another-source.example/"
    ]
  }
}
```

Optional fields:

- `start_date`: inclusive `YYYY-MM-DD` date. Overrides `lookback_days`.
- `end_date`: inclusive `YYYY-MM-DD` date. Defaults to now.
- `fetch_article_text`: boolean, default `true`.
- `include_undated`: boolean, default `false`.

## Markdown Output Contract

`news-feed.md` is the canonical artifact. It must contain:

1. YAML-style frontmatter with `news_feed_schema`, `generated_at`,
   `start_date`, `end_date`, and `total_articles`.
2. One `news-feed-payload` HTML comment containing source metadata.
3. One `news-feed-item-start` / `news-feed-item-end` block per article.

Article metadata comment shape:

```json
{
  "source_name": "str",
  "source_url": "str",
  "title": "str",
  "url": "str",
  "published_at": "str",
  "status": "ok|thin_content|failed",
  "word_count": 0,
  "content_source": "str",
  "summary": "str"
}
```

The article body between the start and end comments is the extracted full text.
The weekly-planner assembler parses this contract into:

```json
{
  "news_feed_data": {
    "schema_version": "1.0",
    "generated_at": "str",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "source_count": 0,
    "total_articles": 0,
    "sources": [{"name": "str", "url": "str", "status": "str"}],
    "articles": [
      {
        "source_name": "str",
        "title": "str",
        "url": "str",
        "published_at": "str",
        "summary": "str",
        "full_text": "str",
        "word_count": 0
      }
    ],
    "markdown_path": "weekly_plans/<YYYY-MM-DD>/news-feed.md"
  }
}
```

## Quality Rules

- Prefer RSS/Atom feeds when available; auto-discover feeds from source homepages.
- Include only articles whose publication date falls inside the requested window,
  unless `include_undated` is true.
- Keep all requested sources in the source metadata even if zero articles are
  found.
- Record failed fetches in `news_feed_report.json`; do not silently drop them.
- Keep extracted text factual. Do not summarize inside `full_text`; summaries
  may be short excerpts from the article body.
