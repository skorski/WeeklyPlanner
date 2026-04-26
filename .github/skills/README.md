# Skills Architecture

This directory contains the agent skills that power the Weekly Family Planner.
Each skill is a self-contained agent with a persona, workflow, and defined data
contract. Skills are organized into five functional layers.

## Layers

```
 ┌─────────────────────────────────────────────────────────────┐
 │  Layer 1: ORCHESTRATION                                     │
 │  weekly-planner — drives the 6-phase pipeline               │
 ├─────────────────────────────────────────────────────────────┤
 │  Layer 2: RESEARCHERS (content producers)                   │
 │  weather · school-calendar · recipes · albums · linkwarden  │
 │  news-feed · dinner-designer · recipe-cards · nutrition-coach│
 │  parenting-coach · stoic-guide · principles · child-wisdom  │
 ├─────────────────────────────────────────────────────────────┤
 │  Layer 3: VALIDATORS (quality gates)                        │
 │  content-validator — pre-assembly (automated)               │
 │  print-formatter — A5 page fitting (PDF only)               │
 │  proofreader — post-render QA (HTML/PDF/MD)                 │
 ├─────────────────────────────────────────────────────────────┤
 │  Layer 4: FORMATTERS (output renderers)                     │
 │  booklet (HTML+PDF) · storybook (flipbook)                  │
 │  weekly-planner/build_plan.py (markdown)                    │
 ├─────────────────────────────────────────────────────────────┤
 │  Layer 5: UTILITIES (standalone tools)                      │
 │  pdf · frontend-design · image-generator · skill-creator    │
 │  final-editor                                               │
 └─────────────────────────────────────────────────────────────┘
```

## 6-Phase Pipeline

```
Phase 1: GATHER ──────► Phase 2: RESEARCH ──────► Phase 3: REVIEW
  Weather, calendars,      Parallel researchers     Content-validator
  favorites, user prefs    ✅ USER SELECTS          checks each output,
                           DINNERS & ALBUMS         loops back to fix
                                │
Phase 4: ASSEMBLE ◄─────────────┘
  Build plan_data.json
  Render markdown draft
  ✅ USER REVIEWS MARKDOWN
  Changes → originating skill → re-validate → re-assemble
                │
Phase 5: FORMAT ◄── (once markdown approved)
  MD (full verbose)
  HTML (full verbose)
  Print-formatter → PDF (trimmed for A5)
                │
Phase 6: QA ◄───────
  Proofreader validates all three outputs
```

### User Checkpoints

| Checkpoint | Phase | What |
|-----------|-------|------|
| Dinner Selection | 2 | User selects 7 dinners, approves albums |
| Markdown Review | 4 | User reviews full draft. Changes route to originating skill. |
| QA Issues | 6 | User notified if proofreader finds failures |

## Skill Inventory

### Orchestration

| Skill | Category | Description |
|-------|----------|-------------|
| `weekly-planner` | orchestration | Drives the 6-phase pipeline from user prompt to rendered outputs |

### Researchers

| Skill | Category | Output | Contract |
|-------|----------|--------|----------|
| `weather` | researcher | `weather.md` | 7-day forecast with temps, conditions, sunshine |
| `school-calendar` | researcher | `school.json` | `{no_school: [], early_release: []}` |
| `recipes` | researcher | `recipes.md` | 10 dinners + appetizers, salads, beverages |
| `albums` | researcher | `album_candidates.json` | ~30 albums with metadata, Spotify URLs |
| `linkwarden` | researcher | `newsletter.json` | Thematic clusters + synthesis + fun section |
| `news-feed` | researcher | `news-feed.md` | Recent source articles with parseable markdown contract |
| `dinner-designer` | researcher | `elevations.json` | Chef tips as `[{type, title, instruction}]` dicts |
| `recipe-cards` | researcher | in plan_data.json | `{nonna_says, engineer_table, variations}` per day |
| `nutrition-coach` | researcher | `nutrition.json` | Daily breakdown + lunch/snack suggestions |
| `parenting-coach` | researcher | `parenting.json` | `{weekly_theme, dinner_questions[], nudges[]}` |
| `stoic-guide` | researcher | `stoic.json` | `{theme, anchor_quote, meditations[], family_exercise}` |
| `principles` | researcher | `principles.json` | `{theme, daily_entries[]}` with 350-450 word essays |
| `child-wisdom` | researcher | `story.json` | `{title, story, discussion_prompt}` |

### Validators

| Skill | Category | When | Purpose |
|-------|----------|------|---------|
| `content-validator` | validator | Phase 3 (pre-assembly) | Checks completeness, quality, field shapes. Loops back to researcher to fix. |
| `print-formatter` | validator | Phase 5 (before PDF) | Trims content to fit A5 pages. Only affects PDF; MD/HTML keep full content. |
| `proofreader` | validator | Phase 6 (post-render) | QA: overflow, content presence, page structure in HTML/PDF/MD. |

### Formatters

| Skill | Category | Output |
|-------|----------|--------|
| `booklet` | formatter | `weekly-plan.html` + `weekly-plan.pdf` |
| `storybook` | formatter | Interactive flipbook HTML + printable PDF |

### Utilities

| Skill | Category | Purpose |
|-------|----------|---------|
| `pdf` | utility | General PDF manipulation (merge, split, forms, OCR) |
| `frontend-design` | utility | Production-grade UI/web design |
| `image-generator` | utility | Image generation via Azure OpenAI (DALL-E 3) |
| `skill-creator` | utility | Guide for creating new skills |
| `final-editor` | utility | Magazine-style editorial polish for plan prose |

## Data Flow

```
masterPrompt.md
    │
    ▼
weekly-planner (orchestrator)
    │
    ├── weather ──────────► weather.md
    ├── school-calendar ──► school.json
    ├── recipes ──────────► recipes.md
    ├── albums ───────────► album_candidates.json
    ├── linkwarden ───────► newsletter.json
    ├── news-feed ────────► news-feed.md
    ├── stoic-guide ──────► stoic.json
    └── principles ───────► principles.json
                │
    ✅ USER SELECTS DINNERS & ALBUMS
                │
    ├── dinner-designer ──► elevations.json
    ├── recipe-cards ─────► (inline in plan)
    ├── parenting-coach ──► parenting.json
    ├── nutrition-coach ──► nutrition.json
    └── child-wisdom ─────► story.json
                │
    content-validator ◄──► researchers (fix loop)
                │
    assemble_plan.py ────► plan_data.json
    final-editor ────────► plan_data.json (enriched)
    build_plan.py ───────► weekly-plan.md
                │
    ✅ USER REVIEWS MARKDOWN
                │
    booklet ─────────────► weekly-plan.html
    print-formatter ─────► plan_data_print.json
    booklet (PDF) ───────► weekly-plan.pdf
                │
    proofreader ─────────► QA report
```

## Three Tiers of Verbosity

| Output | Verbosity | Content |
|--------|-----------|---------|
| `weekly-plan.md` | **Full** | Complete recipes, long descriptions, full essays |
| `weekly-plan.html` | **Full** | Same as MD with collapsible sections |
| `weekly-plan.pdf` | **Print-optimized** | Trimmed by print-formatter to fit A5 pages |

## Critical Field Shape Contract

Templates silently render blank sections when field types are wrong. All
researcher outputs must match these shapes:

| Field | Required Type | Wrong (renders blank) |
|-------|--------------|----------------------|
| `day.dinner_question` | `{question, why}` dict | plain string |
| `day.dinner_elevation_tips[]` | `[{type, title, instruction}]` | formatted strings |
| `day.recipe_card` | `{nonna_says, engineer_table, variations}` | `null` or missing |
| `stoic_data.theme` | `{title, category, description}` | plain string |
| `stoic_data.meditations[]` | array of dicts | key named `days` |
| `principles_data.daily_entries[]` | array with `essay` | key named `days` |
| `principles_data.theme` | `{title, description}` | plain string |
| `parenting_data.weekly_theme` | `{title, description}` | plain string |
| `parenting_data.dinner_questions[]` | array of dicts | key named `days` |
| `news_feed_data.sources` | array of source dicts | missing after requested news feed |
| `news_feed_data.articles[]` | array with `title`, `url`, `source_name`, `full_text` | unparsed markdown |
