---
name: weekly-planner
description: >
  Create a weekly family planner that organizes dinners, activities, and schedules
  into a structured report. Takes unstructured information about the upcoming week
  (events, restrictions, preferences, commitments) and produces a research-style
  markdown plan covering Sunday through Sunday. Use this skill when the user asks
  to plan their week, organize family dinners, create a weekly schedule, or needs
  help deciding what to cook or do during the week. Also triggers on requests for
  meal planning, weekly meal prep, or family activity planning.
---

# Weekly Family Planner

Orchestrate the `weather`, `recipes`, and `albums` skills to produce a unified
Sunday-to-Sunday family plan with dinners, music pairings, and activities.

## Workflow

### Step 1: Parse the User's Free-Text Input

The user provides unstructured text about their week. Extract:

- **Specific recipe/day assignments** (e.g., "tacos on Tuesday") -- these are locked in.
- **Food preferences** -- ingredients, cuisines, dietary restrictions.
- **Music mood/preferences** -- genre, vibe, artist references.
- **Known commitments** -- meetings, kids' activities, travel, social events.
- **Weekend plans** -- outings, errands, rest days.

Ask follow-up questions only if critical information is missing (the week range,
or whether they have hard dietary restrictions). Keep it to 2-3 questions max.

### Step 2: Determine the Plan Folder

All output for a weekly plan goes into `weekly_plans/<YYYY-MM-DD>/` where the date
is the **starting Sunday** of the plan week. Create this folder early — all skill
markdown output (weather, recipes, albums, and the final plan) goes here.

```
weekly_plans/
  2026-02-08/
    weather.md
    recipes.md
    albums.md
    weekly-plan.md
```

### Step 3: Fetch Weather

Invoke the `weather` skill to get the forecast for the target week:

```bash
python .github/skills/weather/scripts/fetch_weather.py --start <YYYY-MM-DD> --end <YYYY-MM-DD> -o weekly_plans/<YYYY-MM-DD>/weather.md
```

### Step 4: Check Work Calendar (if workIq MCP server available)

If the `workIq` MCP server is available, query the user's work calendar to identify:

- Late meetings that affect dinner timing (5:00 PM - 8:00 PM window)
- Work-from-home vs. office days
- Weekend work commitments or evening events

### Step 5: Invoke the Recipes Skill

Pass the user's food preferences (ingredients, cuisines, restrictions) to the
`recipes` skill. This produces a curated list of:

- 10 dinner recipes (diverse cuisines, varied complexity)
- 2 vegetarian dinners
- 2 appetizers, 4 salads, 3 beverage pairings

The recipes skill handles its own web searches. Feed it the extracted food
preferences from Step 1 as the prompt. Save the output markdown to
`weekly_plans/<YYYY-MM-DD>/recipes.md`.

### Step 6: Invoke the Albums Skill

Pass the user's music preferences (mood, genre, vibe -- or derive from the week's
theme if not specified) to the `albums` skill. This produces ~30 album
recommendations with metadata. Save the output markdown to
`weekly_plans/<YYYY-MM-DD>/albums.md`.

### Step 7: Present Options and Get User Selections

Present the user with a summary of:

1. **Available dinners** -- the recipe list from Step 4
2. **Available albums** -- the album list from Step 5
3. **Pre-assigned days** -- any recipe/day locks from the original prompt

Ask the user to:

- **Select 7 dinners** for the week (Sunday through Saturday) from the recipe list
- **Optionally assign specific recipes to specific days** -- or allow auto-assignment
- **Select albums** they like -- or allow automatic pairing

Respect any assignments the user made in the original prompt (e.g., "tacos on
Tuesday" means tacos are locked to Tuesday). The user may also say "pick for me"
for some or all days.

### Step 8: Auto-Assign Remaining Days

For days without user-specified assignments:

- **Dinners:** Assign considering time constraints (quick meals on busy nights,
  elaborate meals on free nights), weather (soups on cold days, grilling on warm
  days), and variety (no repeating proteins or cuisines back-to-back).
- **Albums:** Pair each dinner with the album whose mood/style best complements the
  meal's cuisine and the day's vibe. Consider: energetic albums for weekend cooking,
  mellow for weeknight wind-down, genre affinity (jazz with French, cumbia with
  Latin, ambient with Asian, etc.).

### Step 9: Nutritional Review

Review the final 7-day dinner lineup as a nutritionist:

- Check protein variety across the week (not all chicken, not all beef)
- Verify vegetable coverage (at least 2-3 servings/day represented)
- Flag if any day is excessively heavy or light
- Suggest swaps or side additions if the week is nutritionally lopsided
- Note any allergen concerns if the user mentioned restrictions

Present findings to the user. If adjustments are needed, swap from the remaining
recipe pool and re-pair albums.

### Step 10: Build the Plan JSON

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
python .github/skills/weekly-planner/scripts/assemble_plan.py days.json \
    -o weekly_plans/<YYYY-MM-DD>/plan_data.json \
    --elevations elevations.json \
    --parenting parenting.json \
    --nutrition nutrition.json
```

The assembler:
- Matches elevations to days by dinner name (case-insensitive)
- Stores parenting data at the top level as `parenting_data`
- Extracts `weekly_nutrition_summary` into `nutrition_summary`
- Uses `utf-8-sig` encoding to handle BOM from Windows/PowerShell

Structure:

```json
{
  "week_range": "February 8 - February 14, 2026",
  "days": [
    {
      "name": "Sun 02/08",
      "long_name": "Sunday, February 8",
      "weather": "Partly cloudy, 45F/32F",
      "weather_detail": "Mostly Sunny (72%), wind 8 mph, 0% precip",
      "calendar": "Soccer practice 10am",
      "calendar_items": ["Soccer practice 10:00 AM"],
      "time_constraints": ["Back from soccer by noon"],
      "dinner": "Slow-Cooker Beef Stew",
      "dinner_cuisine": "American",
      "dinner_description": "Rich, hearty stew with root vegetables...",
      "dinner_key_ingredients": ["beef chuck", "carrots", "potatoes", "red wine"],
      "dinner_source_url": "https://example.com/recipe",
      "dinner_source_name": "Serious Eats",
      "dinner_notes": "Start before soccer; ready by 5 PM",
      "dinner_nutrition_notes": "Good iron from beef; add a side salad for greens",
      "album": "Miles Davis - Kind of Blue",
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

### Step 11: Final Editorial Pass

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

### Step 12: Render the Report

If you used the modular approach (Option B), `assemble_plan.py` already wrote
`plan_data.json` to the correct folder. Now render the markdown:

```bash
python .github/skills/weekly-planner/scripts/build_plan.py weekly_plans/<YYYY-MM-DD>/plan_data.json
```

The output defaults to `weekly-plan.md` inside the folder. You can override the
filename (but not the folder) with `-o`:

```bash
python .github/skills/weekly-planner/scripts/build_plan.py plan_data.json -o weekly-plan.md
```

### Step 13: Generate Booklet (optional)

If the user wants a printable PDF or mobile HTML, invoke the **booklet** skill.
Keep the plan JSON file around until after the booklet is generated:

```bash
python .github/skills/booklet/scripts/render_booklet.py plan_data.json
```

This produces `weekly-plan.html` and `weekly-plan.pdf` in the same
`weekly_plans/<YYYY-MM-DD>/` folder.

### Step 14: Clean Up

Remove the temporary JSON file after all rendering is complete.

## Output Format

The rendered report includes:

1. **Week-at-a-glance table** -- day, weather, dinner, and album at a glance
2. **Daily breakdown** -- expanded detail per day: weather, calendar, dinner recipe
   info, album info with pairing rationale, activity, and prep notes
3. **Appetizers & salads** -- the selected accompaniments with full details
4. **Beverage pairings** -- drink suggestions for the week
5. **Grocery & prep summary** -- consolidated shopping list and prep-ahead checklist
6. **Nutrition summary** -- brief nutritional review of the week
7. **Additional notes** -- batch cooking tips, leftovers strategy

## Guidelines

- **All markdown output goes in `weekly_plans/<YYYY-MM-DD>/`** where the date is the
  starting Sunday of the plan week. This includes `weather.md`, `recipes.md`,
  `albums.md`, and `weekly-plan.md`. The `build_plan.py` script creates the folder
  automatically; for other skill outputs, pass the folder path via `-o`.
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
