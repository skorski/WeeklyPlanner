---
name: albums
description: >
  Discover unique album recommendations based on a freeform prompt (mood, genre,
  artist reference, or any combination). Searches Bandcamp, Pitchfork, Discogs, and
  Bands In Town for diverse results, then enriches each album with detailed metadata
  via the Discogs API. The number of albums is configurable (default ~30). Bands In
  Town results always focus on artists with upcoming shows in the DC area within 6
  months. Outputs a markdown file with year, producer, label, sonic style, lyrical
  themes, mood, and tracklist so an expert can pick 7 albums from the list.
  Use this skill when the user asks for music recommendations, album lists, or
  playlist inspiration.
---

# Album Discovery Skill

Discover and curate album recommendations from a freeform prompt, enriched
with detailed metadata from Discogs. Album count is configurable to manage
Discogs API rate limits.

## Workflow

This skill requires the agent to perform web searches and then pass results to the
enrichment script. Follow these steps **in order**:

### Step 0: Check Past Plans for Variety

Before starting album research, scan `weekly_plans/*/plan_data.json` for albums
from the last 4 weeks to avoid recommending the same music:

```python
import json, glob
past_plans = sorted(glob.glob("weekly_plans/*/plan_data.json"))
recent = past_plans[-4:]
past_albums = []
for path in recent:
    data = json.load(open(path))
    for day in data.get("days", []):
        if day.get("album"):
            past_albums.append(day["album"])
```

Do not include any album from `past_albums` in the curated list unless the user
explicitly requests it.

### Step 1: Determine Album Count

The user may request a specific number of albums. If not specified, default to **30**.
Keep in mind:
- Discogs enrichment takes ~1 second per album (rate limiting at 60 req/min)
- For 10 albums: ~15 seconds. For 30 albums: ~35 seconds. For 50 albums: ~60 seconds.
- Gather **10–15 more candidates** than the target to allow for dedup and filtering.

### Step 2: Search for Album Recommendations

Run **6 separate web searches** using the `web_search` tool to gather candidates from
different sources. Adapt the user's prompt into search queries:

1. `site:bandcamp.com "<user prompt>" album` — Bandcamp results
2. `site:pitchfork.com best albums "<user prompt>"` — Pitchfork reviews/lists
3. `site:discogs.com "<user prompt>" album` — Discogs catalog
4. `site:bandsintown.com "<user prompt>" concerts Washington DC` — **Bands In Town:
   ALWAYS focus on artists/bands with upcoming shows in the DC metro area within the
   next 6 months.** Include the venue, date, and city in the album entry's description.
5. `"<user prompt>" album recommendations` — General recommendations
6. `"<user prompt>" essential albums list` — Curated lists

From all 6 searches, compile a list of candidates (target + 10–15 extra).
Ensure variety:
- Mix well-known and obscure picks
- Span multiple decades/eras where relevant
- Include different subgenres within the prompt's scope
- Note which source each album came from
- **Bands In Town entries MUST include upcoming DC-area show info** (venue, date, city)
  in the `description` and `upcoming_show` fields

There should be a variety in the albums. Some nights may need more energetic music to balance out a long day.
Ensure the descriptions for the search are not consistently vague like "cozy" or "dinner party".

### Step 3: Build Candidate JSON

Create a temporary JSON file with the candidates. Each entry should have:

```json
[
  {
    "artist": "Artist Name",
    "title": "Album Title",
    "source": "bandcamp|pitchfork|discogs|bandsintown|web",
    "year": "2024",
    "description": "Brief note on why this album fits the prompt",
    "lyrical_themes": "Themes and subject matter (no copyrighted lyrics)",
    "mood": "Emotional tone and atmosphere",
    "sonic_description": "Sound, production style, instrumentation",
    "upcoming_show": "Mar 15, 2026 @ 9:30 Club, Washington DC"
  }
]
```

The `upcoming_show` field is **required for bandsintown-sourced entries** and optional
for others. Fill in `description`, `lyrical_themes`, `mood`, and `sonic_description`
from your knowledge. The `year`, `producer`, `label`, `genres`, `styles`, and
`tracklist` fields will be enriched automatically by the Discogs API in Step 4.

### Step 4: Run the Enrichment Script

```bash
python scripts/discover_albums.py candidates.json -p "<user prompt>" -o <output-path> --limit <N>
```

Set `--limit` to the user's requested album count (default 30).

The script will:
1. Deduplicate by artist + title
2. Search Discogs for each album and enrich with: year, label, producer, genres, styles,
   tracklist, country, format
3. Limit to the specified count
4. Render via the Jinja2 template to markdown

### Step 5: Clean Up

Remove the temporary JSON candidates file.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-p`, `--prompt` | The original search prompt | "Album discovery" |
| `-o`, `--output` | Output markdown file path | stdout |
| `--skip-enrich` | Skip Discogs API enrichment | false |
| `--limit` | Max albums to include | 30 |

## Output Format

The generated markdown contains:
1. **Summary table** — quick-scan with #, artist, album, year, sonic style, source
2. **Detailed entries** — full metadata per album:
   - Year, label, producer, genre, sonic style, country, format
   - Why this album fits the prompt
   - Lyrical themes and mood (copyright-safe descriptions, not full lyrics)
   - Sonic description
   - Collapsible tracklist with durations

## Configuration

- **Discogs token** is stored in `.env` in the skill directory
- Requires Python 3.7+ and: `jinja2`, `python-dotenv`
- The template is in `templates/album_list.md.j2` — edit to customize output
