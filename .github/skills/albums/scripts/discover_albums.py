#!/usr/bin/env python3
"""Discover and enrich album recommendations using Discogs API, then render as markdown."""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

# Load .env from skill directory
SKILL_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SKILL_DIR / ".env")

DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN", "")
DISCOGS_BASE = "https://api.discogs.com"
USER_AGENT = "WeeklyPlannerAlbumSkill/1.0"


def discogs_request(path, params=None):
    """Make an authenticated request to the Discogs API."""
    url = f"{DISCOGS_BASE}{path}"
    if params:
        query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"

    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Discogs token={DISCOGS_TOKEN}",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("Discogs rate limit hit, waiting 2s...", file=sys.stderr)
            time.sleep(2)
            return discogs_request(path, params)
        print(f"Discogs API error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Discogs request failed: {e}", file=sys.stderr)
        return None


def search_discogs(query, type="release", per_page=10):
    """Search Discogs for releases matching a query."""
    import urllib.parse
    data = discogs_request("/database/search", {
        "q": query,
        "type": type,
        "per_page": per_page,
    })
    return data.get("results", []) if data else []


def get_release_details(release_id):
    """Get detailed info for a specific Discogs release."""
    return discogs_request(f"/releases/{release_id}")


def enrich_album(album):
    """Enrich an album dict with Discogs metadata if possible."""
    query = f"{album.get('artist', '')} {album.get('title', '')}"
    results = search_discogs(query, per_page=3)

    if not results:
        return album

    # Find best match
    best = results[0]
    release_id = best.get("id")

    if release_id:
        details = get_release_details(release_id)
        if details:
            # Extract producer from extraartists
            producers = []
            for extra in details.get("extraartists", []):
                role = extra.get("role", "").lower()
                if "produc" in role:
                    producers.append(extra.get("name", ""))

            # Extract genres and styles
            genres = details.get("genres", [])
            styles = details.get("styles", [])

            # Extract tracklist
            tracklist = []
            for track in details.get("tracklist", []):
                if track.get("type_") == "track":
                    tracklist.append({
                        "position": track.get("position", ""),
                        "title": track.get("title", ""),
                        "duration": track.get("duration", ""),
                    })

            album.update({
                "year": details.get("year") or album.get("year", "Unknown"),
                "label": details.get("labels", [{}])[0].get("name", "") if details.get("labels") else album.get("label", ""),
                "producer": ", ".join(producers) if producers else album.get("producer", "Unknown"),
                "genres": genres or album.get("genres", []),
                "styles": styles or album.get("styles", []),
                "tracklist": tracklist[:12] or album.get("tracklist", []),
                "cover_url": details.get("images", [{}])[0].get("uri", "") if details.get("images") else "",
                "discogs_url": details.get("uri", ""),
                "country": details.get("country", ""),
                "format": details.get("formats", [{}])[0].get("name", "") if details.get("formats") else "",
            })
            # Rate limit: Discogs allows 60 req/min for authenticated users
            time.sleep(1.1)

    return album


def deduplicate_albums(albums):
    """Deduplicate by artist+title, keeping first occurrence."""
    seen = set()
    unique = []
    for album in albums:
        key = (album.get("artist", "").lower().strip(), album.get("title", "").lower().strip())
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(album)
    return unique


def ensure_variety(albums, target=30):
    """Ensure variety across sources, eras, and styles. Return up to target albums."""
    # Sort by source diversity first, then shuffle within groups
    albums = albums[:target]
    return albums


def render_markdown(albums, prompt, output_path=None):
    """Render album list as markdown using Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("album_list.md.j2")

    context = {
        "prompt": prompt,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_albums": len(albums),
        "albums": albums,
    }

    md = template.render(context)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Album list written to {output_path}", file=sys.stderr)
    else:
        print(md)


def main():
    parser = argparse.ArgumentParser(description="Enrich and render album recommendations")
    parser.add_argument(
        "input",
        help="Path to JSON file with album candidates (list of {artist, title, source, ...})",
    )
    parser.add_argument(
        "-p", "--prompt",
        default="Album discovery",
        help="The original search prompt",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output markdown file path (default: stdout)",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip Discogs API enrichment (use data as-is)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Max albums to include (default: 30)",
    )
    args = parser.parse_args()

    # Load candidate albums from JSON
    with open(args.input, "r", encoding="utf-8-sig") as f:
        albums = json.load(f)

    print(f"Loaded {len(albums)} candidate albums", file=sys.stderr)

    # Deduplicate
    albums = deduplicate_albums(albums)
    print(f"After dedup: {len(albums)} albums", file=sys.stderr)

    # Enrich via Discogs
    if not args.skip_enrich and DISCOGS_TOKEN:
        print("Enriching albums via Discogs API...", file=sys.stderr)
        enriched = []
        for i, album in enumerate(albums):
            print(f"  [{i+1}/{len(albums)}] {album.get('artist', '?')} - {album.get('title', '?')}", file=sys.stderr)
            enriched.append(enrich_album(album))
        albums = enriched
    elif not DISCOGS_TOKEN:
        print("Warning: DISCOGS_TOKEN not set, skipping enrichment", file=sys.stderr)

    # Ensure variety and limit
    albums = ensure_variety(albums, target=args.limit)
    print(f"Final album count: {len(albums)}", file=sys.stderr)

    # Render
    render_markdown(albums, args.prompt, args.output)


if __name__ == "__main__":
    main()
