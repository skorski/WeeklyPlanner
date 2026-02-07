---
name: recipes
description: >
  Curate a diverse weekly dinner menu from a freeform prompt containing desired dishes
  and ingredients. Produces 10 dinner recipes with diverse cuisine origins, plus 2
  appetizers, 2+ salads, and 2 beverage pairings. Use this skill when the user asks
  for dinner ideas, weekly meal planning, recipe suggestions, or menu creation.
  The user will select from the curated list to build their weekly menu.
---

# Recipe Recommender Skill

Curate a diverse set of dinner recipes, appetizers, salads, and beverage pairings
from a freeform prompt. The user provides desired dishes and/or ingredients, and the
skill produces a varied list for weekly menu selection.

## Workflow

This skill is entirely agent-driven using web search. Follow these steps **in order**:

### Step 0: Check Past Plans for Variety

Before starting recipe research, scan `weekly_plans/*/plan_data.json` for dinners
from the last 4 weeks to avoid recommending the same dishes:

```python
import json, glob
past_plans = sorted(glob.glob("weekly_plans/*/plan_data.json"))
recent = past_plans[-4:]
past_dinners = []
for path in recent:
    data = json.load(open(path))
    for day in data.get("days", []):
        if day.get("dinner"):
            past_dinners.append(day["dinner"])
```

If the user explicitly requests a repeat dish, allow it. Otherwise, do not include
any dinner from `past_dinners` in the curated list.

### Step 1: Parse the User's Prompt

Extract from the user's input:
- **Desired dishes** (e.g., "pasta", "tacos", "stir fry")
- **Desired ingredients** (e.g., "chicken", "mushrooms", "seasonal vegetables")
- **Dietary restrictions** if mentioned (e.g., "vegetarian", "gluten-free")
- **Cuisine preferences** if mentioned (e.g., "Mediterranean", "Asian-inspired")

### Step 2: Search for Recipes

Run **4–5 web searches** using the `web_search` tool, adapting queries to the user's
prompt. Aim for **cuisine diversity** — spread across at least 5 different culinary
traditions (e.g., Italian, Japanese, Mexican, Indian, Middle Eastern, French, Thai, Korean, Peruvian).

There should always be at least one italian recipe and one Middle Eastern one.
If the user specifies a protein, like beef, always provide at least a second option.
IE, not all recipes should have the ingredients the user requested.
There should always be some adjacent recipes that have a similar flavor style but vastly different ingredients.

Stay away from the standard "chicken sheet pan" options. You can have one or two but the goal is to have diversity.
Never recommend etheopian food. This is always purchased out due to the complexity.

Example searches:
1. `"<ingredient>" dinner recipe site:seriouseats.com OR site:bonappetit.com or site:foodandwine.com`
2. `"<dish>" recipe site:food52.com OR site:epicurious.com or site:foodandwine.com`
3. `"<ingredient>" "<cuisine>" dinner recipe`
4. `appetizer salad pairing "<ingredient>" recipe recommendations`
5. `"<dish>" beverage wine beer pairing`

### Step 3: Compile the Recipe List

From search results and your culinary knowledge, compile:

- **10 dinner recipes** — diverse origins, varied cooking methods, mix of complexity
- **2 Vegetarian dinners** - Also diverse origins, ensure these have no meat.
- **2 appetizers** — complementary to the dinner options
- **4 salads** — see **Salad Requirements** below
- **3 beverage pairings** — wine, beer, cocktail, or non-alcoholic options

Salads should be part of the dinner selection as well. We eat at least one salad per week for dinner.

**Salad Requirements:**

The salad section is critical. Produce exactly **4 salads** in these categories:

1. **Composed Salad (Dinner-sized)** — Artfully arranged, not tossed. Should be
   substantial enough to serve as a standalone dinner. Think composed Niçoise,
   a grain bowl with arranged components, or a structured plate with layered elements.

2. **Tossed Salad (Dinner-sized)** — A generous, well-dressed tossed salad hearty
   enough to be a full meal. Should have protein or substantial grains/legumes.

3. **Side Salad #1** — Any style (leafy, slaw, grain, etc.) designed to complement
   the dinner recipes on the list.

4. **Side Salad #2** — Any style, different from Side Salad #1.

**For ALL salads, you MUST include:**
- **Salad type** label: `composed_dinner`, `tossed_dinner`, `side`, or `side`
- **Seasonal focus**: Use produce that is **in season on the US East Coast** for the
  current time of year. In winter: citrus, hearty greens (kale, radicchio, endive),
  root vegetables, winter squash, pomegranate, persimmon, stored apples/pears,
  cabbage, Brussels sprouts, beets. In summer: stone fruit, tomatoes, corn, berries,
  cucumbers, herbs, peppers. Adjust for the actual season.
- **Specific dressing recipe**: Name the dressing, list exact ingredients (oil, acid,
  emulsifier, seasonings). Don't just say "vinaigrette" — say "sherry vinaigrette
  with Dijon mustard, minced shallot, sherry vinegar, extra-virgin olive oil, honey,
  salt, and black pepper."
- **Flavor rationale**: Explain in 2-3 sentences WHY these ingredients and dressing
  work together — what flavor principles are at play (e.g., bitter + sweet + acid,
  umami + crunch, fat + bright citrus). Describe the intent behind the combination.
- **Theme alignment**: Salads should reflect the user's requested theme where possible
  (e.g., if the prompt is "beef and Super Bowl," a hearty winter slaw or Mexican-inspired
  salad fits better than a light spring mix).

**Diversity requirements:**
- At least 4 different cuisine origins across the 10 dinners
- Mix of proteins (or protein-free if vegetarian)
- Variety in cooking methods (braised, grilled, roasted, raw, sautéed, etc.)
- At least 2 vegetarian-friendly options among the 10 dinners

### Step 4: Expand and review

Based on the recipes, appetizers, and drinks, do a second search for things that would make each of them better.
Look for additional recipes to add that are less traditional and will provide more of a flavor adventure to the diner.

### Step 4: Build and Write the Markdown Output

Create the output markdown file using the Jinja2 template. Build a JSON-compatible
data structure and pass it to the rendering script:

```bash
python scripts/render_recipes.py candidates.json -p "<user prompt>" -o <output-path>
```

Each recipe entry in the JSON should have:

```json
{
  "name": "Recipe Name",
  "category": "dinner|appetizer|salad|beverage",
  "cuisine": "Italian",
  "description": "Brief 1-2 sentence description of the dish",
  "key_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
  "source_url": "https://example.com/recipe",
  "source_name": "Serious Eats",
  "why": "Brief note on why this fits the prompt and adds variety"
}
```

**For salad entries, add these additional fields:**

```json
{
  "name": "Winter Citrus & Radicchio Salad",
  "category": "salad",
  "salad_type": "composed_dinner|tossed_dinner|side",
  "cuisine": "Italian",
  "description": "Composed arrangement of blood orange segments, shaved radicchio...",
  "key_ingredients": ["blood oranges", "radicchio", "burrata", "pistachios", "Castelvetrano olives"],
  "dressing": "Blood orange vinaigrette: fresh blood orange juice, champagne vinegar, Dijon mustard, extra-virgin olive oil, minced shallot, flaky salt, cracked black pepper",
  "flavor_rationale": "The bitter radicchio is tamed by sweet citrus segments and creamy burrata, while the acid in the vinaigrette brightens every bite. Pistachios add crunch and richness. This combination follows the Italian principle of balancing amaro (bitter) with dolce (sweet) and grasso (fat).",
  "seasonal_note": "Blood oranges and radicchio are at their peak on the East Coast in January–March.",
  "source_url": "https://example.com/recipe",
  "source_name": "Food52",
  "why": "Dinner-sized composed salad — stunning presentation, seasonal winter citrus"
}
```

### Step 5: Clean Up

Remove the temporary JSON file.

## Output Format

The generated markdown contains:
1. **Dinner Recipes** — 10 options in a summary table + detail cards
2. **Appetizers** — 2 starters that complement the dinner options
3. **Salads** — 4 salads: 1 composed dinner, 1 tossed dinner, 2 sides — each with
   specific dressing recipe, flavor rationale, and seasonal notes
4. **Beverage Pairings** — 3 drink suggestions with pairing notes

Each entry includes: name, cuisine origin, brief description, key ingredients,
source URL, and a note on why it was selected.

## Configuration

- Requires Python 3.7+ and `jinja2`
- Template is in `templates/menu_suggestions.md.j2` — edit to customize output
- No API keys required — uses web search for recipe discovery
