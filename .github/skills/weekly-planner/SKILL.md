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

### Step 2: Fetch Weather

Invoke the `weather` skill to get the forecast for the target week:

```bash
python .github/skills/weather/scripts/fetch_weather.py --start <YYYY-MM-DD> --end <YYYY-MM-DD>
```

### Step 3: Check Work Calendar (if workIq MCP server available)

If the `workIq` MCP server is available, query the user's work calendar to identify:

- Late meetings that affect dinner timing (5:00 PM - 8:00 PM window)
- Work-from-home vs. office days
- Weekend work commitments or evening events

### Step 4: Invoke the Recipes Skill

Pass the user's food preferences (ingredients, cuisines, restrictions) to the
`recipes` skill. This produces a curated list of:

- 10 dinner recipes (diverse cuisines, varied complexity)
- 2 vegetarian dinners
- 2 appetizers, 4 salads, 3 beverage pairings

The recipes skill handles its own web searches. Feed it the extracted food
preferences from Step 1 as the prompt. Save the output markdown for reference.

### Step 5: Invoke the Albums Skill

Pass the user's music preferences (mood, genre, vibe -- or derive from the week's
theme if not specified) to the `albums` skill. This produces ~30 album
recommendations with metadata. Save the output markdown for reference.

### Step 6: Present Options and Get User Selections

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

### Step 7: Auto-Assign Remaining Days

For days without user-specified assignments:

- **Dinners:** Assign considering time constraints (quick meals on busy nights,
  elaborate meals on free nights), weather (soups on cold days, grilling on warm
  days), and variety (no repeating proteins or cuisines back-to-back).
- **Albums:** Pair each dinner with the album whose mood/style best complements the
  meal's cuisine and the day's vibe. Consider: energetic albums for weekend cooking,
  mellow for weeknight wind-down, genre affinity (jazz with French, cumbia with
  Latin, ambient with Asian, etc.).

### Step 8: Nutritional Review

Review the final 7-day dinner lineup as a nutritionist:

- Check protein variety across the week (not all chicken, not all beef)
- Verify vegetable coverage (at least 2-3 servings/day represented)
- Flag if any day is excessively heavy or light
- Suggest swaps or side additions if the week is nutritionally lopsided
- Note any allergen concerns if the user mentioned restrictions

Present findings to the user. If adjustments are needed, swap from the remaining
recipe pool and re-pair albums.

### Step 9: Build the Plan JSON

Build a temporary JSON file. Structure:

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
      "activity": "Board game afternoon",
      "activity_notes": "Too cold for outdoor activities",
      "prep_notes": ["Thaw stew meat Saturday night"]
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
  ]
}
```

### Step 10: Render the Report

```bash
python .github/skills/weekly-planner/scripts/build_plan.py plan_data.json -o weekly-plan.md
```

### Step 11: Clean Up

Remove the temporary JSON file after rendering.

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

- Respect user's explicit day assignments from their original prompt above all else
- Favor practical meals (30-60 min weeknights, more elaborate on free days)
- Include at least one leftover-reuse opportunity
- Match meals and activities to weather when data is available
- Album pairings should feel intentional, not random -- explain the pairing
- The nutritional review should be helpful, not preachy
- The template is in `templates/weekly_plan.md.j2` -- edit to customize output
- Requires Python 3.7+ and `jinja2`
