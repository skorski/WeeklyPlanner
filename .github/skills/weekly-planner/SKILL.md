---
name: weekly-planner
category: orchestration
description: >
  Create a weekly family planner that organizes dinners, activities, and schedules
  into a structured report. Takes unstructured information about the upcoming week
  (events, restrictions, preferences, commitments) and produces a research-style
  markdown plan covering Sunday through Sunday. Use this skill when the user asks
  to plan their week, organize family dinners, create a weekly schedule, or needs
  help deciding what to cook or do during the week. Also triggers on requests for
  meal planning, weekly meal prep, family activity planning, or adding news
  sources/news feeds to the weekly plan.
---

# Weekly Family Planner

Orchestrate the `weather`, `recipes`, and `albums` skills to produce a unified
Sunday-to-Sunday family plan with dinners, music pairings, and activities.

## Workflow

The planner runs as a **6-phase pipeline**. Each phase must complete before the
next begins. Two phases contain mandatory user checkpoints (marked 🛑) where
execution pauses for user input.

```
Phase 1: GATHER → Phase 2: RESEARCH → Phase 3: REVIEW
    → Phase 4: ASSEMBLE → Phase 5: FORMAT → Phase 6: QA
```

---

### Phase 1: GATHER

Collect all inputs and contextual data needed for the plan.

#### 1.1 Parse the User's Free-Text Input

The user provides unstructured text about their week. Extract:

- **Specific recipe/day assignments** (e.g., "tacos on Tuesday") -- these are locked in.
- **Food preferences** -- ingredients, cuisines, dietary restrictions.
- **Elsie's no-go list** -- ask what Elsie doesn't want to eat this week. Kids' food
  preferences change weekly, so always ask. Store the list for display in the plan.
- **Music mood/preferences** -- genre, vibe, artist references.
- **News feed sources** -- named publications, homepages, RSS/Atom feeds, or
  article sources the user wants monitored for recent posts.
- **Known commitments** -- meetings, kids' activities, travel, social events.
- **Weekend plans** -- outings, errands, rest days.

Ask follow-up questions only if critical information is missing (the week range,
or whether they have hard dietary restrictions). **Always ask what Elsie doesn't
want to eat this week** — this is a required question, not optional.

#### 1.2 Determine the Plan Folder

All output for a weekly plan goes into `weekly_plans/<YYYY-MM-DD>/` where the date
is the **starting Sunday** of the plan week. Create this folder early — all skill
markdown output (weather, recipes, albums, and the final plan) goes here.

```
weekly_plans/
  2026-02-08/
    weather.md
    recipes.md
    albums.md
    news-feed.md
    weekly-plan.md
```

#### 1.3 Fetch Weather and School Calendar

Invoke the `weather` skill to get the forecast for the target week:

```bash
python .github/skills/weather/scripts/fetch_weather.py --start <YYYY-MM-DD> --end <YYYY-MM-DD> -o weekly_plans/<YYYY-MM-DD>/weather.md
```

Invoke the `school-calendar` skill to check for days off or early releases:

```bash
python .github/skills/school-calendar/scripts/lookup_school_calendar.py --start <YYYY-MM-DD> --end <YYYY-MM-DD> -o weekly_plans/<YYYY-MM-DD>/school.json
```

If there are **no-school days**, add them to the relevant day's `calendar_items`
(e.g., "No School — Thanksgiving Break"). If there are **early release days**,
add those too (e.g., "Early Release — End of Quarter 1"). A day off means Elsie
is home all day, which may affect meal timing, activity planning, or dinner
complexity.

#### 1.4 Check Work Calendar (if workIq MCP server available)

If the `workIq` MCP server is available, query the user's work calendar to identify:

- Late meetings that affect dinner timing (5:00 PM - 8:00 PM window)
- Work-from-home vs. office days
- Weekend work commitments or evening events

---

### Phase 2: RESEARCH

Run researcher skills in two waves. Wave 1 has no inter-skill dependencies and
runs **in parallel**. Wave 2 depends on the user's dinner and album selections
from the checkpoint between the waves.

#### Wave 1 — Parallel Research (no dependencies)

Launch all applicable Wave 1 skills simultaneously (six total when news-feed
sources are provided):

**2.1 Invoke the Recipes Skill**

Pass the user's food preferences (ingredients, cuisines, restrictions) to the
`recipes` skill. This produces a curated list of:

- 10 dinner recipes (diverse cuisines, varied complexity)
- 2 vegetarian dinners
- 2 appetizers, 4 salads, 3 beverage pairings

The recipes skill handles its own web searches. Feed it the extracted food
preferences from Phase 1 as the prompt. Save the output markdown to
`weekly_plans/<YYYY-MM-DD>/recipes.md`.

**2.2 Invoke the Albums Skill**

Pass the user's music preferences (mood, genre, vibe -- or derive from the week's
theme if not specified) to the `albums` skill. This produces ~30 album
recommendations with metadata. Save the output markdown to
`weekly_plans/<YYYY-MM-DD>/albums.md`.

**2.3 Invoke the Weekly Read Source Ingestion + Linkwarden Skill**

Fetch the user's recent reading from Linkwarden and any user-provided URLs,
RSS/Atom feeds, or required topics. This has no dependencies on dinner selections.

```bash
python .github/skills/linkwarden/scripts/fetch_reading_sources.py \
  --input weekly_plans/<YYYY-MM-DD>/week_request.json \
  -o weekly_plans/<YYYY-MM-DD>/reading_sources.json \
  --report weekly_plans/<YYYY-MM-DD>/reading_ingestion_report.json
```

Then follow the linkwarden SKILL.md workflow to:
1. Read and absorb all successful source records
2. Group into 2–4 thematic clusters
3. Write reflective synthesis for each cluster
4. Find or search for a fun section
5. Research additional perspectives via web search
6. Output `newsletter.json` to `weekly_plans/<YYYY-MM-DD>/`

Every user-requested URL must appear in `reading_sources.json`. Every successfully
extracted source should appear in a newsletter cluster or in
`newsletter_data.not_used_sources` with a reason. The newsletter data is merged
via `--newsletter` in the assembly phase.

**2.4 Invoke the News Feed Skill**

If the user provides news sources, source homepages, RSS/Atom feeds, or asks to
monitor publications like Bellingcat, store them in `week_request.json` under
`news_feed`:

```json
{
  "news_feed": {
    "lookback_days": 7,
    "max_items_per_source": 5,
    "sources": [
      {"name": "Bellingcat", "url": "https://www.bellingcat.com/"},
      {"name": "David Heinemeier Hansson", "feed_url": "https://world.hey.com/dhh/feed.atom"},
      {"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index"},
      {"name": "Hacker News", "feed_url": "https://news.ycombinator.com/rss"}
    ]
  }
}
```

Then invoke the `news-feed` skill:

```bash
python .github/skills/news-feed/scripts/fetch_news_feed.py \
  --input weekly_plans/<YYYY-MM-DD>/week_request.json \
  -o weekly_plans/<YYYY-MM-DD>/news-feed.md \
  --report weekly_plans/<YYYY-MM-DD>/news_feed_report.json
```

The news-feed skill writes `news-feed.md` as the canonical artifact. It contains
parseable contract comments plus the extracted article text. The assembler merges
it via `--news-feed` into top-level `news_feed_data`.

**2.5 Invoke the Stoic Guide Skill**

Create the weekly Stoic reflection guide. This only needs the week's calendar
context.

Follow the stoic-guide SKILL.md workflow to:
1. Check past plans for theme variety (avoid repeating last 8 weeks)
2. Choose a theme based on the week's calendar, season, and emotional context
3. Research the classical source and modern commentary
4. Build the progressive meditation sequence
5. Include a family exercise and young stoic section
6. Output `stoic.json` to `weekly_plans/<YYYY-MM-DD>/`

The stoic data is merged via `--stoic` in the assembly phase.

**2.6 Invoke the Principles Skill**

Create the weekly "Principles for Living" guide. This only needs the week's
calendar context.

Follow the principles SKILL.md workflow to:
1. Check past plans for theme variety (avoid repeating last 8 weeks)
2. Choose a weekly theme and primary thinker
3. Research the original source and supporting perspectives
4. Write 7 daily mini-essays (200–300 words each, one per day Sun–Sat)
5. Output `principles.json` to `weekly_plans/<YYYY-MM-DD>/`

The principles data is merged via `--principles` in the assembly phase.
Each daily entry becomes its own A5 page in the booklet (page 2 of each day's
3-page spread).

#### 🛑 USER CHECKPOINT — Dinner & Album Selection

This is a **mandatory stop**. Do not proceed to Wave 2 without user input.

Present the user with a summary of:

1. **Available dinners** — the recipe list from Step 2.1
2. **Available albums** — the album list from Step 2.2
3. **Pre-assigned days** — any recipe/day locks from the original prompt

Ask the user to:

- **Select 7 dinners** for the week (Sunday through Saturday) from the recipe list
- **Optionally assign specific recipes to specific days** — or allow auto-assignment
- **Approve albums** they like — or allow automatic pairing

Respect any assignments the user made in the original prompt (e.g., "tacos on
Tuesday" means tacos are locked to Tuesday). The user may also say "pick for me"
for some or all days.

#### Auto-Assign Remaining Days

For days without user-specified assignments:

- **Dinners:** Assign considering time constraints (quick meals on busy nights,
  elaborate meals on free nights), weather (soups on cold days, grilling on warm
  days), and variety (no repeating proteins or cuisines back-to-back).
- **Albums:** Pair each dinner with the album whose mood/style best complements the
  meal's cuisine and the day's vibe. Consider: energetic albums for weekend cooking,
  mellow for weeknight wind-down, genre affinity (jazz with French, cumbia with
  Latin, ambient with Asian, etc.).

#### Wave 2 — Post-Selection Research (depends on user choices)

Launch all five skills after the user has selected dinners and approved albums:

**2.6 Invoke the Dinner-Designer Skill**

Pass the 7 selected dinners to the `dinner-designer` skill for chef's elevations
(sauces, marinades, texture contrasts, temperature play). Save output to
`weekly_plans/<YYYY-MM-DD>/elevations.json`.

**2.7 Invoke the Recipe-Cards Skill**

Pass the 7 selected dinners to the `recipe-cards` skill for detailed cooking
instructions, Cooking-for-Engineers step tables, and recipe variations. Save
output to `weekly_plans/<YYYY-MM-DD>/recipe_cards.json`.

**2.8 Invoke the Parenting-Coach Skill**

Pass the weekly plan context (dinners, activities, calendar) to the
`parenting-coach` skill for dinner conversation starters, developmental nudges,
and connection rituals. Save output to `weekly_plans/<YYYY-MM-DD>/parenting.json`.

**2.9 Invoke the Nutrition-Coach Skill**

Pass the 7 selected dinners to the `nutrition-coach` skill for nutritional
analysis, deficiency/excess flagging, and lunch/snack recommendations. Save
output to `weekly_plans/<YYYY-MM-DD>/nutrition.json`.

**2.10 Invoke the Child-Wisdom Skill**

Pass the week's theme and context to the `child-wisdom` skill to write a short
illustrated-style children's mystery story with a life lesson. Save output to
`weekly_plans/<YYYY-MM-DD>/story.json`.

---

### Phase 3: REVIEW

Validate all researcher output before assembly. This phase invokes the
**content-validator** skill to catch structural or quality issues early.

#### 3.1 Run Content Validation

The content-validator reads all researcher output files from
`weekly_plans/<YYYY-MM-DD>/`:

- `recipes.md`, `albums.md`, `newsletter.json`, `stoic.json`, `principles.json`
- `news-feed.md` when `week_request.json` contains `news_feed.sources`
- `elevations.json`, `recipe_cards.json`, `parenting.json`, `nutrition.json`, `child-wisdom.json`

It validates:
- **Field shapes** — required keys present, correct types (strings, arrays, objects)
- **Completeness** — no empty or placeholder values, all 7 days covered where applicable
- **Quality** — descriptions meet minimum length, no obvious template artifacts

#### 3.2 Handle Validation Failures

If the content-validator finds issues:

1. **Generate fix instructions** describing exactly what is wrong and what the
   corrected output should look like.
2. **Re-invoke the failing researcher skill** with the fix instructions appended
   to the original prompt.
3. **Re-run the content-validator** on the updated output.
4. **Maximum 2 retries** per skill. If a skill still fails after 2 retries,
   **escalate to the user** with a summary of what is wrong and which skill
   cannot produce valid output.

The content-validator **must pass on all files** before proceeding to Phase 4.

---

### Phase 4: ASSEMBLE

Build the unified plan data, apply editorial polish, render a markdown draft,
and get user approval.

#### 4.1 Elsie's No-Go Check

After dinners are assigned, cross-reference each dinner's key ingredients and
cuisine against Elsie's no-go list from Phase 1. This does **not** change the
selected recipes — the dinners stand as planned. Instead:

1. Store `elsie_no_list` at the top level of `plan_data.json` (array of strings).
2. For each day, if the dinner contains or features something on Elsie's no-go
   list, add an `elsie_note` string to that day's entry. The note should:
   - Acknowledge the conflict warmly (e.g., "Elsie's not a fan of mushrooms this week")
   - Offer one small, practical substitution or workaround (e.g., "Set aside her
     portion before adding mushrooms, or swap in zucchini for her plate")
   - Keep it brief — 1-2 sentences max
3. If a dinner has no conflict, omit `elsie_note` for that day.

Example:
```json
"elsie_no_list": ["mushrooms", "olives", "spicy food"],
"days": [
  {
    "dinner": "Wild Mushroom Risotto",
    "elsie_note": "Elsie's not into mushrooms this week — make her portion plain risotto with extra parmesan and butter, stirred in before the mushrooms go in."
  }
]
```

#### 4.2 Build the Plan JSON

Build a temporary JSON file containing the core plan structure (days, appetizers,
salads, beverages, grocery list, prep tasks, notes). The supporting skill data
(elevations, parenting, nutrition) can be kept in separate JSON files and merged
using the `assemble_plan.py` script.

**Option A: Single JSON (all-in-one)**
Build one JSON file with everything inline, including `dinner_elevation_tips` on
each day, `parenting_data`, and `nutrition_summary`. Skip `assemble_plan.py`.

**Option B: Modular assembly (recommended)**
Write just the core days/menus JSON, then use `assemble_plan.py` to merge:

```bash
python .github/skills/weekly-planner/scripts/assemble_plan.py \
    weekly_plans/<YYYY-MM-DD>/days.json \
    -o weekly_plans/<YYYY-MM-DD>/plan_data.json \
    --elevations    weekly_plans/<YYYY-MM-DD>/elevations.json \
    --parenting     weekly_plans/<YYYY-MM-DD>/parenting.json \
    --nutrition     weekly_plans/<YYYY-MM-DD>/nutrition.json \
    --newsletter    weekly_plans/<YYYY-MM-DD>/newsletter.json \
    --news-feed     weekly_plans/<YYYY-MM-DD>/news-feed.md \
    --stoic         weekly_plans/<YYYY-MM-DD>/stoic.json \
    --principles    weekly_plans/<YYYY-MM-DD>/principles.json \
    --child-wisdom  weekly_plans/<YYYY-MM-DD>/child-wisdom.json \
    --recipe-cards  weekly_plans/<YYYY-MM-DD>/recipe_cards.json
```

All required researcher outputs, plus optional outputs requested by the user,
must be passed in. Omitting a flag silently drops that content from the booklet
— for example, skipping `--recipe-cards` leaves every day page without the
"Mamma Karen Says" block and Variations, and skipping `--news-feed` leaves
requested sources out of `plan_data.json`. If using `--week-dir`, the assembler
auto-detects `news-feed.md`.
Run `assemble_plan.py` from the **repository root**, never from inside
`weekly_plans/<date>/` (that creates a nested-path bug).

After assembly, **re-run the content-validator on `plan_data.json`** to catch
any day that ended up without a `recipe_card`, `dinner_elevation_tips`, or
`dinner_question` (see Phase 3 — Step 6 in content-validator/SKILL.md).

The assembler:
- Matches elevations to days by dinner name (case-insensitive)
- Stores parenting data at the top level as `parenting_data`
- Maps parenting `dinner_questions` onto each day's `dinner_question` field by `day_of_week`
- Extracts `weekly_nutrition_summary` into `nutrition_summary`
- Stores newsletter data at the top level as `newsletter_data`
- Parses `news-feed.md` and stores it at the top level as `news_feed_data`
- Uses `utf-8-sig` encoding to handle BOM from Windows/PowerShell

**Normalized fields** (added automatically by `assemble_plan.py`):
- `day_of_week` — lowercase day name ("sunday", "monday", ...) for reliable cross-skill joining
- `weather_high`, `weather_low` — integer temperatures extracted from the freeform `weather` string
- `weather_condition` — uppercase condition label (SUNNY, OVERCAST, RAIN, etc.)
- `weather_emoji` — emoji for the condition (☀️, ☁️, 🌧️, etc.)
- `weather_oneliner` — contextual one-liner like "45°/32° · warmest day, gusty"
- `album_artist`, `album_title` — split from the "Artist – Title" format in `album`
- `engagements` — structured array of `{time, event, event_short}` parsed from `calendar_items`
- `dinner_question` — matched from `parenting_data.dinner_questions` by `day_of_week`

These fields eliminate the need for regex parsing in downstream consumers (booklet renderer, webapp).

Structure:

```json
{
  "week_range": "February 8 - February 14, 2026",
  "elsie_no_list": ["mushrooms", "olives"],
  "days": [
    {
      "name": "Sun 02/08",
      "long_name": "Sunday, February 8",
      "day_of_week": "sunday",
      "weather": "Partly cloudy, 45F/32F",
      "weather_detail": "Mostly Sunny (72%), wind 8 mph, 0% precip",
      "weather_high": 45,
      "weather_low": 32,
      "weather_condition": "PARTLY CLOUDY",
      "weather_emoji": "⛅",
      "weather_oneliner": "45°/32° · warmest day",
      "calendar": "Soccer practice 10am",
      "calendar_items": ["Soccer practice 10:00 AM"],
      "engagements": [
        { "time": "10:00 AM", "event": "Soccer practice", "event_short": "Soccer practice" }
      ],
      "time_constraints": ["Back from soccer by noon"],
      "dinner": "Slow-Cooker Beef Stew",
      "dinner_cuisine": "American",
      "dinner_description": "Rich, hearty stew with root vegetables...",
      "dinner_key_ingredients": ["beef chuck", "carrots", "potatoes", "red wine"],
      "dinner_source_url": "https://example.com/recipe",
      "dinner_source_name": "Serious Eats",
      "dinner_notes": "Start before soccer; ready by 5 PM",
      "dinner_nutrition_notes": "Good iron from beef; add a side salad for greens",
      "elsie_note": "Elsie's not into mushrooms this week — set aside her portion before adding the mushroom gravy, and top with extra butter instead.",
      "album": "Miles Davis – Kind of Blue",
      "album_artist": "Miles Davis",
      "album_title": "Kind of Blue",
      "album_year": "1959",
      "album_genre": "Jazz",
      "album_mood": "Contemplative, warm",
      "album_description": "The quintessential modal jazz album...",
      "album_sonic_description": "Smooth trumpet, gentle piano, walking bass...",
      "album_pairing_rationale": "Sunday stew simmering calls for unhurried jazz",
      "album_spotify_url": "https://open.spotify.com/album/...",
      "activity": "Board game afternoon",
      "activity_notes": "Too cold for outdoor activities",
      "prep_notes": ["Thaw stew meat Saturday night"],
      "dinner_elevation_tips": [
        {
          "type": "Sauce",
          "title": "Red Wine Reduction",
          "instruction": "After braising, strain 1 cup liquid and reduce by half with a splash of balsamic for a glossy finishing sauce."
        },
        {
          "type": "Texture",
          "title": "Crispy Shallots",
          "instruction": "Top with thinly sliced shallots fried until golden — adds crunch contrast to the tender meat."
        }
      ],
      "dinner_question": {
        "day": "Sunday",
        "dinner": "Slow-Cooker Beef Stew",
        "question": "If you could cook any meal for someone you love, what would you make?",
        "category": "imagination",
        "why": "Encourages empathy and creative thinking through food"
      },
      "prep_detail": {
        "prep_timeline": "3-4 hours (mostly hands-off braising)",
        "prep_steps": [
          "Step 1 with full detail and measurements...",
          "Step 2 with technique notes..."
        ],
        "active_time": "45 minutes",
        "special_equipment": ["Dutch oven", "Sharp knife"],
        "make_ahead": "Stew can be made a day ahead. Reheat gently."
      }
    }
  ],
  "appetizers": [
    {
      "name": "Whipped Feta Dip",
      "cuisine": "Mediterranean",
      "description": "...",
      "key_ingredients": ["feta", "cream cheese", "lemon", "herbs"]
    }
  ],
  "salads": [
    {
      "name": "Winter Citrus & Radicchio",
      "salad_type": "composed_dinner",
      "description": "...",
      "dressing": "Blood orange vinaigrette...",
      "flavor_rationale": "..."
    }
  ],
  "beverages": [
    {
      "name": "Malbec",
      "description": "Full-bodied red, pairs with beef and stews",
      "why": "Complements the hearty Sunday stew"
    }
  ],
  "grocery_list": {
    "Produce": ["carrots", "celery", "potatoes"],
    "Protein": ["2 lbs beef chuck", "1 lb chicken thighs"],
    "Pantry": ["crushed tomatoes", "chicken broth"]
  },
  "prep_ahead": [
    "Saturday: Thaw stew meat for Sunday",
    "Sunday: Chop vegetables for Monday and Tuesday"
  ],
  "nutrition_summary": "Good protein variety (beef, chicken, fish, vegetarian). Consider adding a leafy side on Wednesday.",
  "notes": [
    "Double the Sunday stew for Monday lunch leftovers"
  ],
  "parenting_data": {
    "weekly_theme": {
      "title": "The Sous Chef",
      "description": "This week, invite your child into the kitchen as a helper. Cooking together builds math skills, confidence, and family connection."
    },
    "dinner_questions": [
      {
        "day": "Sunday",
        "dinner": "Braised Short Ribs",
        "question": "If you could cook any meal for someone you love, what would you make?",
        "why": "Encourages empathy and creative thinking through food"
      }
    ],
    "nudges": [
      {
        "title": "Measure & Pour",
        "context": "Cooking involves real math — fractions, volume, temperature.",
        "suggestion": "Let your child handle all the measuring this week.",
        "how_to": [
          "Show them how to read a measuring cup",
          "Let them figure out 'half of 3/4 cup'",
          "Celebrate their accuracy (or laugh together at the mess)"
        ]
      }
    ],
    "recommendation": {
      "title": "Stirring Up Fun!",
      "author": "Deanna F. Cook",
      "why": "Age-appropriate recipes that give kids real ownership of a dish.",
      "connection": "Pairs perfectly with this week's Sous Chef theme."
    },
    "parent_reflection": "What is one skill you learned by doing — not by being told? How can you create that experience for your child this week?"
  }
}
```

#### 4.3 Final Editorial Pass

Invoke the **final-editor** skill to polish the plan copy before rendering.
The editor enriches thin content, adds day introductions, rewrites terse
descriptions into engaging prose, and creates thematic connective tissue.

The editor works on `plan_data.json` in place:

1. Read `plan_data.json` and identify thin content (terse descriptions,
   missing day intros, generic album notes)
2. Run web searches (1 per dinner + 1 per album) for real editorial detail
3. Write day introductions connecting weather → calendar → dinner
4. Rewrite dinner and album descriptions with specificity and warmth
5. Polish the cover highlight, notes, and nutrition summary
6. Build an edits JSON and apply it:

```bash
python .github/skills/final-editor/scripts/edit_plan.py \
    weekly_plans/<YYYY-MM-DD>/plan_data.json \
    --edits edits.json \
    --report weekly_plans/<YYYY-MM-DD>/editorial-report.md
```

The editorial report lets the user review all changes before rendering.

#### 4.4 Render Markdown Draft

Render the markdown from the assembled and edited `plan_data.json`:

```bash
python .github/skills/weekly-planner/scripts/build_plan.py weekly_plans/<YYYY-MM-DD>/plan_data.json
```

The output defaults to `weekly-plan.md` inside the folder. You can override the
filename (but not the folder) with `-o`:

```bash
python .github/skills/weekly-planner/scripts/build_plan.py plan_data.json -o weekly-plan.md
```

#### 🛑 USER CHECKPOINT — Plan Review

This is a **mandatory stop**. Present the full rendered markdown to the user for
review before proceeding to formatting.

If the user requests changes:

1. **Identify the originating skill** responsible for the content that needs
   changing (e.g., a dinner description → dinner-designer, an album note →
   albums, a conversation starter → parenting-coach).
2. **Re-invoke that skill** with the user's change request appended to the
   original prompt.
3. **Run the content-validator** (Phase 3) on the updated output.
4. **Re-assemble** the plan (repeat Steps 4.2–4.4).
5. **Re-render** the markdown and present again.

**Do NOT create custom fix scripts** — all content changes must flow through
the originating skill so its internal logic and quality checks apply.

---

### Phase 5: FORMAT

Produce the three deliverable formats: markdown (already done), HTML, and PDF.

#### 5.1 Render HTML

Generate the mobile-friendly HTML from the full `plan_data.json`:

```bash
python .github/skills/booklet/scripts/render_booklet.py weekly_plans/<YYYY-MM-DD>/plan_data.json --html-only
```

This produces `weekly-plan.html` in the `weekly_plans/<YYYY-MM-DD>/` folder.

#### 5.2 Create Print-Optimized JSON

The **print-formatter** skill is documentation-only today — there is no
`print_formatter.py` script. For now, copy `plan_data.json` verbatim to
`plan_data_print.json` and let the booklet CSS handle A5 fit:

```powershell
Copy-Item weekly_plans/<YYYY-MM-DD>/plan_data.json `
          weekly_plans/<YYYY-MM-DD>/plan_data_print.json -Force
```

```bash
# bash / zsh equivalent
cp weekly_plans/<YYYY-MM-DD>/plan_data.json \
   weekly_plans/<YYYY-MM-DD>/plan_data_print.json
```

If specific pages overflow, trim the offending fields by hand in
`plan_data_print.json` (the full copy stays in `plan_data.json` so HTML and
markdown remain verbose). When the print-formatter skill ships its script,
replace this copy step with the invocation.

#### 5.3 Render PDF

Generate the printable PDF from the print-optimized JSON:

```bash
python .github/skills/booklet/scripts/render_booklet.py weekly_plans/<YYYY-MM-DD>/plan_data_print.json --pdf-only
```

This produces `weekly-plan.pdf` in the `weekly_plans/<YYYY-MM-DD>/` folder.

---

### Phase 6: QA

Validate all three outputs and report any issues to the user.

#### 6.1 Invoke the Proofreader

Run the **proofreader** skill on all three deliverables:

- `weekly_plans/<YYYY-MM-DD>/weekly-plan.md` (markdown)
- `weekly_plans/<YYYY-MM-DD>/weekly-plan.html` (HTML)
- `weekly_plans/<YYYY-MM-DD>/weekly-plan.pdf` (PDF)

The proofreader checks:
- Page overflow in HTML/PDF
- All plan content (dinners, albums, chef's tips, conversation starters, events)
  appears on the correct pages
- Page numbering sequence is valid
- Section order matches the expected layout

#### 6.2 Handle QA Failures

If the proofreader finds failures, **report them to the user** with:
- Which output(s) failed
- What specific issues were found
- Suggested corrective action (e.g., "re-run Phase 5 after trimming day intro
  on Wednesday" or "album description on Thursday overflows — shorten by ~20 words")

Do not auto-fix QA failures — present them for user decision.

## Output Format

The rendered report includes:

1. **Week-at-a-glance table** -- day, weather, dinner, and album at a glance
2. **Daily breakdown** -- expanded detail per day: weather, calendar, dinner recipe
   info, album info with pairing rationale, activity, and prep notes
3. **Appetizers & salads** -- the selected accompaniments with full details
4. **Beverage pairings** -- drink suggestions for the week
5. **Grocery & prep summary** -- consolidated shopping list and prep-ahead checklist
6. **News feed** -- requested source list and recent article excerpts when provided
7. **Nutrition summary** -- brief nutritional review of the week
8. **Additional notes** -- batch cooking tips, leftovers strategy

## Guidelines

- **All markdown output goes in `weekly_plans/<YYYY-MM-DD>/`** where the date is the
  starting Sunday of the plan week. This includes `weather.md`, `recipes.md`,
  `albums.md`, `news-feed.md`, and `weekly-plan.md`. The `build_plan.py` script
  creates the folder automatically; for other skill outputs, pass the folder path
  via `-o`.
- Respect user's explicit day assignments from their original prompt above all else
- Favor practical meals (30-60 min weeknights, more elaborate on free days)
- Include at least one leftover-reuse opportunity
- Match meals and activities to weather when data is available
- Album pairings should feel intentional, not random -- explain the pairing
- The nutritional review should be helpful, not preachy
- The template is in `templates/weekly_plan.md.j2` -- edit to customize output
- Requires Python 3.7+ and `jinja2`

## Variety Across Weeks

Before finalizing the plan, **scan all existing `weekly_plans/*/plan_data.json`
files** to check what has been used in previous weeks. This ensures the family
doesn't eat the same meals or listen to the same albums on repeat.

### What to check:
- **Dinners:** Extract `days[].dinner` from each past plan. Avoid repeating any
  dinner that appeared in the last 4 weeks. If the user explicitly requests a
  repeat, that's fine — but the agent should not auto-assign a recent repeat.
- **Albums:** Extract `days[].album` from each past plan. Avoid re-pairing any
  album used in the last 4 weeks.
- **Cuisines:** Check cuisine distribution across the last 4 weeks. If Italian
  appeared 3 times last week, lean toward other cuisines this week.
- **Proteins:** Check protein sources across recent weeks. Ensure variety over time
  (don't do beef 5 times in 2 weeks).

### How to check:
```python
import json, glob
past_plans = sorted(glob.glob("weekly_plans/*/plan_data.json"))
recent = past_plans[-4:]  # last 4 weeks
for path in recent:
    data = json.load(open(path))
    for day in data.get("days", []):
        print(day.get("dinner"), day.get("album"))
```

Flag any conflicts to the user: "Persian Lamb Stew was on last week's menu —
want to keep it, or should I suggest an alternative?"
