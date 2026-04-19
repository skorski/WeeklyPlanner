---
name: child-wisdom
category: researcher
description: >
  Write a short illustrated-style children's mystery story (250-800 words) with
  a life lesson woven in. The story's theme aligns with the parenting coach's
  weekly theme, and elements from the week (dinner ingredients, album moods,
  weather, family activities) appear as subtle details in the narrative. Use
  this skill when the user asks to "write a kids story," "add a bedtime story,"
  "create a story for the booklet," or as part of the weekly planner workflow.
---

# Child Wisdom — Weekly Mystery Story

Write a short children's mystery story for the back page of the weekly family
planner booklet. The story is designed to be read aloud at bedtime or at the
dinner table — a 3-5 minute read that sparks conversation.

## Story Formula

Every story follows this structure:

1. **The Setup** (~80-160 words) — Introduce a child protagonist (age 7-9,
   gender-neutral name) in a familiar setting. Something small but puzzling
   happens — a missing object, a strange sound, a note with no author.

2. **The Investigation** (~120-400 words) — The protagonist follows clues. Each
   clue connects to a sensory detail (smell, sound, texture). The mystery
   deepens but never becomes scary — it's curiosity-driven, not fear-driven.

3. **The Reveal** (~80-160 words) — The answer is surprising but warm. The
   "mystery" turns out to be an act of kindness, a misunderstanding, or a
   natural phenomenon. No villains — only discoveries.

4. **The Wisdom** (~40-80 words) — A single closing line or short paragraph
   that names the life lesson without being preachy. Written as the
   protagonist's own realization, not an adult's lecture.

## Inputs

The story draws from two sources:

### From the parenting coach (`parenting.json`)
- `weekly_theme.title` — the moral/emotional theme (e.g., "Love in Action")
- `weekly_theme.description` — context for the theme
- `parent_reflection` — the deeper lesson to encode

### From the plan data (`plan_data.json`)
- Dinner ingredients and cuisines — appear as sensory details
- Weather conditions — set the atmosphere
- Album moods — influence the story's emotional tone
- Family activities — can inspire the setting

## Output

A JSON file with this structure:

```json
{
  "title": "The Case of the Warm Mittens",
  "story": "Full story text with paragraph breaks...",
  "theme": "Love in Action",
  "life_lesson": "Sometimes the biggest kindnesses are the ones nobody sees.",
  "reading_time": "3-5 minutes",
  "discussion_prompt": "Has anyone ever done something kind for you without telling you?"
}
```

Save as `child-wisdom.json` in the week folder.

## Workflow

### Step 1: Gather Inputs
Read the parenting theme and plan data:
```bash
# These files should already exist from earlier skills
cat weekly_plans/<date>/parenting.json    # weekly_theme, reflection
cat weekly_plans/<date>/plan_data.json    # days with dinners, weather, albums
```

### Step 2: Write the Story
Using the formula above, write a story that:
- Embeds the weekly theme as the life lesson
- Uses 2-3 sensory details from the week's meals
- Matches the week's emotional tone (from album moods)
- Features weather or setting details from the forecast
- Is appropriate for an 8-year-old reader/listener
- Contains a small mystery that resolves warmly
- Stays between 250-800 words

### Step 3: Save Output
```bash
# Save the story JSON
echo '{ "title": "...", "story": "...", ... }' > weekly_plans/<date>/child-wisdom.json
```

### Step 4: Integration
The booklet skill picks up `child-wisdom.json` via `assemble_plan.py`:
```bash
python assemble_plan.py days.json --child-wisdom child-wisdom.json ...
```

The story renders on the back pages of the booklet (up to two pages) to ensure
there is room for a valid and strong story arc.

## Style Guide

- **Voice**: Third person, past tense, warm and unhurried
- **Vocabulary**: Age-appropriate but not dumbed down — use one "delicious"
  word per story that a child might ask about (e.g., "iridescent," "peculiar")
- **Tone**: Cozy mystery, not thriller — think Encyclopedia Brown meets
  Frog and Toad
- **Length**: 250-800 words (story may span multiple pages in the booklet)
- **No**: Violence, scares, sadness, moralistic lecturing, talking animals
  (unless the week's theme calls for it)
- **Yes**: Sensory details, small kindnesses, child agency, satisfying
  resolutions, quiet wonder

## Character Bible

The stories share a recurring cast. Use the right character for the setting and
give each appearance a **fresh note** — do not recycle the same trait line
every week.

### Chelsie (the child)
- 8 years old, curious, literal, loves Babo Pasta, loyal to her family.
- Speaks in short, honest sentences.
- Occasionally shrieks, whispers, or goes very quiet when thinking.

### Mamma Karen (Italian grandmother)
- Calls Chelsie **piccola**.
- Refers to Dan as **her son** or **my son** — **never "my boy"**.
- Speaks about the house and its rooms with definite articles: **the pantry**,
  **the kitchen**, **the table** — **not "my pantry" / "my kitchen"**. Mamma
  Karen owns the love, not the square footage.
- Warm, teasing, patient. Ends scenes with small rituals (puts the kettle on,
  pats a cheek, tucks a napkin).
- Tells stories about Dan's childhood with affectionate embarrassment.

### Papa Puleo (Italian grandfather)
- Cooks, wears an apron, uses food metaphors ("Slow is how the flavor builds").
- Can share scenes with Mamma Karen.

### Daddio (Dan, the dad, as a character in stories *about* him)
- Rolls out the pasta on the pasta machine, cooks dinner, grills, makes the pizza.
  **Dad cooks.** Do not default to Mamma Karen or Laura doing the home cooking
  in the current-day household.
- His childhood house/yard was a **different house in a different place** — do
  not draw "the same garden where Daddio once..." connections to the current
  home. You may compare *types* of things (dirt is dirt, rain is rain) but
  never the same physical location.

### Mr. Bugles (sock puppet)
- Lives on Chelsie's **left hand**, indoor/kitchen/car settings.
- Shouts IN CAPS or whispers dramatically.
- **Forbidden repeat phrases** — do not reuse these in new stories:
  - "with absolutely no filter" / "who had absolutely no filter"
  - Any other fixed epithet longer than 3 words that has appeared in a
    previous week's `child-wisdom.json`.
- Each appearance should reveal something **new** about him: a new fear, a
  new obsession, a new opinion, a new skill, a new piece of backstory. Before
  writing, skim the last 3 weeks of `child-wisdom.json` for the traits
  already used and pick a fresh one.

### Mertle (turtle sock puppet)
- A **turtle sock puppet** with a soft cotton shell, a small green head, and
  bright button eyes that always look slightly up to something.
- Rides in Chelsie's jacket pocket outdoors; suns himself on the windowsill
  indoors. Lives at the boundary between house and outside world.
- **Calmer than Mr. Bugles, and wittier.** Dry, wry, professorial. Deadpan
  one-liners rather than ALL-CAPS shouting. Raises a stubby arm before
  speaking. Closes his button eyes when something is delicious or appalling.
- Loves nature facts (the Earth's tilt, spring peepers, skunk cabbage, how
  turtles handle winter). Speaks about the natural world with quiet
  authority.
- Has a **signature little shimmy move** he does at the end of a scene.
- Use Mertle when the story is outdoor or nature-adjacent, or when the scene
  needs a calm, witty counterweight to a louder voice.

### Choosing Mr. Bugles vs. Mertle
- Fully indoor, kitchen-counter silliness → **Mr. Bugles** leads.
- Outdoor, nature, weather, or quiet/thoughtful scenes → **Mertle** leads.
- They can appear together; when they do, Bugles is the volume and Mertle is
  the wit.

## Anti-Repeat Checklist (run before saving)

1. Read the last 3–4 `child-wisdom.json` files in `weekly_plans/*/`.
2. List every trait line or catchphrase attributed to Mr. Bugles, Mertle,
   Mamma Karen, or Papa Puleo.
3. If any sentence in the new story closely matches one of those lines,
   rewrite it.
4. Ensure the chosen puppet (Bugles or Mertle) learns or reveals something
   **not** present in the last 4 stories.
5. Check Mamma Karen's dialog: **"my son"** not "my boy"; **"the pantry"**
   not "her pantry" / "my pantry".
6. Check who is doing the cooking in the current household: **Dad** rolls
   pasta, grills, makes dumplings, makes pizza.
7. Do not claim the current home is where Daddio grew up. That was a
   different house in a different yard.

## Output Contract

The content-validator checks this output before assembly. All fields are required
unless marked optional.

```json
{
  "title": "str",
  "story": "str (250-800 words)",
  "theme": "str",
  "life_lesson": "str",
  "characters": ["str"],
  "discussion_prompt": "str"
}
```

### Validation Rules
- `title` must be non-empty
- `story` must be 250-800 words
- `discussion_prompt` must be non-empty
- `characters` is an array of character names appearing in the story

## Configuration
- No external dependencies — the story is written by the LLM
- No API keys required
- Output: single JSON file
