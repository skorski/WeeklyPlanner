---
name: booklet
category: formatter
description: >
  Generate a mobile-friendly HTML file and a printable PDF from a weekly
  plan. The PDF contains individual A5 pages (148mm × 210mm) in reading order with
  minimalist design. Supports extensible extra sections that other skills can add
  (parenting tips, articles, etc.). Use this skill after the weekly-planner skill
  has produced its plan data. Triggers on requests to "make a booklet," "create a
  PDF," "print the plan," or "make the plan mobile-friendly."
---

# Weekly Plan Booklet

Generate a mobile-friendly **HTML file** and a printable **PDF booklet** from a
weekly plan. This skill runs **after** the weekly-planner skill has produced its
plan JSON data file.

## Output

Both files are written to `weekly_plans/<YYYY-MM-DD>/`:

```
weekly_plans/2026-02-08/
  weekly-plan.md      ← from weekly-planner skill
  weather.md          ← from weather skill
  recipes.md          ← from recipes skill
  albums.md           ← from albums skill
  weekly-plan.html    ← mobile-friendly (this skill)
  weekly-plan.pdf     ← printable booklet (this skill)
```

## PDF Format

- **Page size:** A5 (148mm × 210mm) — individual pages in reading order
- **Printing:** Use Adobe Reader's booklet printing feature if a folded booklet is desired
- **Style:** Minimalist, editorial — muted palette, serif headings, clean typography
- **Structure:** Traditional booklet with section dividers, running headers, and page numbers
- **Page order:**
  1. Cover — week title, date range, hero highlight
  2. Week at a Glance — overview summary table
  3. **Section divider** — "Daily Plan"
  4–31. Daily pages — 4-page spread per day × 7 days (running header: DAILY PLAN)
     - Page 1: Day overview — weather, events, dinner, conversation starter
     - Page 2: Principles — daily mini-essay from the weekly principles theme
     - Page 3: Recipe — nonna's instructions + engineer merge-flow table
     - Page 4: Variations + chef's tips + album pairing
  32. **Section divider** — "Kitchen & Pantry"
  12. Appetizers & Salads
  13. Beverage Pairings
  14. Grocery List
  15. Prep-Ahead Checklist
  16. **Section divider** — "Family Corner"
  17–18. Parenting Corner — theme, dinner questions, nudges, reflection
  19+. Extra sections (extensible — see below)
  Last. Back cover — notes, nutrition summary, colophon

Pages are output sequentially in reading order by `render_booklet.py`.
Content flows naturally across pages when it exceeds a single A5 sheet.
Adobe Reader (or any PDF viewer) can handle booklet folding at print time.

## Extensibility

Other skills (e.g., parenting tips, weekly articles) can add pages to the booklet
by providing an `extra_sections` JSON file:

```json
[
  {
    "title": "Parenting Corner",
    "content": "<p>This week's tip: screen time boundaries for Gen Alpha...</p>"
  },
  {
    "title": "Interesting Read",
    "content": "<p>Article summary and link...</p>"
  }
]
```

Pass it via the `--extra-sections` flag.

## Workflow

### Step 1: Locate the Plan Data

Find the plan JSON file. This is the same file used by the weekly-planner skill's
`build_plan.py` script. It should be in the working directory or the user will
specify its path.

If only the rendered `weekly-plan.md` exists (no JSON), ask the user to re-run the
weekly planner or provide the JSON.

### Step 2: Generate HTML and PDF

```bash
python .github/skills/booklet/scripts/render_booklet.py plan_data.json
```

This command:
- Reads the plan JSON
- Auto-detects the week folder from `week_range`
- Writes `weekly-plan.html` and `weekly-plan.pdf` to `weekly_plans/<YYYY-MM-DD>/`

**Options:**
```bash
# Specify output directory explicitly
python .github/skills/booklet/scripts/render_booklet.py plan_data.json -o weekly_plans/2026-02-08/

# HTML only (skip PDF)
python .github/skills/booklet/scripts/render_booklet.py plan_data.json --html-only

# PDF only (skip HTML)
python .github/skills/booklet/scripts/render_booklet.py plan_data.json --pdf-only

# Add extra sections from another skill
python .github/skills/booklet/scripts/render_booklet.py plan_data.json --extra-sections parenting.json

# Check if any day pages overflow their single-page bounds (used by final-editor)
python .github/skills/booklet/scripts/render_booklet.py plan_data.json --check-overflow
```

The `--check-overflow` flag renders the HTML, then uses Playwright to measure
each `.page-day` element's scroll height against the available page height. If
any day page overflows, it prints structured `OVERFLOW_PAGES` JSON and exits
with code 1. The final-editor skill uses this in an iterative loop to ensure
editorial copy fits before the plan is finalized.

### Step 3: Clean Up

Remove the temporary plan JSON file if it was created just for this step.

## Configuration

- Requires Python 3.7+, `jinja2`, and `playwright`
- Playwright Chromium must be installed: `python -m playwright install chromium`
- `pypdf` is optional (used only for page count reporting)
- Template is in `templates/booklet.html.j2` — edit to customize layout and styling
- The HTML uses `@media screen` for mobile and `@media print` for the PDF
- No API keys required
