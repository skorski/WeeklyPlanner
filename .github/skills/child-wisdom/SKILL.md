---
name: child-wisdom
description: >
  Write a short illustrated-style children's mystery story (250-400 words) with
  a life lesson woven in. The story's theme aligns with the parenting coach's
  weekly theme, and elements from the week (dinner ingredients, album moods,
  weather, family activities) appear as subtle details in the narrative. Use
  this skill when the user asks to "write a kids story," "add a bedtime story,"
  "create a story for the booklet," or as part of the weekly planner workflow.
---

# Child Wisdom — Weekly Mystery Story

Write a short children's mystery story for the back page of the weekly family
planner booklet. The story is designed to be read aloud at bedtime or at the
dinner table — a 2-3 minute read that sparks conversation.

## Story Formula

Every story follows this structure:

1. **The Setup** (~80 words) — Introduce a child protagonist (age 7-9,
   gender-neutral name) in a familiar setting. Something small but puzzling
   happens — a missing object, a strange sound, a note with no author.

2. **The Investigation** (~120 words) — The protagonist follows clues. Each
   clue connects to a sensory detail (smell, sound, texture). The mystery
   deepens but never becomes scary — it's curiosity-driven, not fear-driven.

3. **The Reveal** (~80 words) — The answer is surprising but warm. The
   "mystery" turns out to be an act of kindness, a misunderstanding, or a
   natural phenomenon. No villains — only discoveries.

4. **The Wisdom** (~40 words) — A single closing line or short paragraph
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
  "reading_time": "2 minutes",
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
- Stays between 250-400 words

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

The story renders on the back page of the booklet, replacing or augmenting
the notes section.

## Style Guide

- **Voice**: Third person, past tense, warm and unhurried
- **Vocabulary**: Age-appropriate but not dumbed down — use one "delicious"
  word per story that a child might ask about (e.g., "iridescent," "peculiar")
- **Tone**: Cozy mystery, not thriller — think Encyclopedia Brown meets
  Frog and Toad
- **Length**: 250-400 words (strict — must fit on a half-letter page)
- **No**: Violence, scares, sadness, moralistic lecturing, talking animals
  (unless the week's theme calls for it)
- **Yes**: Sensory details, small kindnesses, child agency, satisfying
  resolutions, quiet wonder

## Configuration
- No external dependencies — the story is written by the LLM
- No API keys required
- Output: single JSON file
