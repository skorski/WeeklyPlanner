---
name: booklet
description: >
  Generate a mobile-friendly HTML file and a printable PDF booklet from a weekly
  plan. The PDF is formatted as a half-letter booklet (5.5" × 8.5" folded) with
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

## PDF Booklet Format

- **Page size:** 11" × 8.5" (letter landscape) with two 5.5" × 8.5" half-pages per sheet
- **Imposition:** Saddle-stitch booklet order — print duplex (flip short edge), stack sheets, fold once in center
- **Style:** Minimalist, editorial — muted palette, serif headings, clean typography
- **Structure:** Traditional booklet with section dividers, running headers, and page numbers
- **Page order (logical, before imposition):**
  1. Cover — week title, date range, hero highlight
  2. Week at a Glance — overview summary table
  3. **Section divider** — "Daily Plan"
  4–10. Daily pages — dinner + album + chef's tips per day (running header: DAILY PLAN)
  11. **Section divider** — "Kitchen & Pantry"
  12. Appetizers & Salads
  13. Beverage Pairings
  14. Grocery List
  15. Prep-Ahead Checklist
  16. **Section divider** — "Family Corner"
  17–18. Parenting Corner — theme, dinner questions, nudges, reflection
  19+. Extra sections (extensible — see below)
  Last. Back cover — notes, nutrition summary, colophon

Pages are automatically padded to a multiple of 4 and imposed in booklet
signature order by `render_booklet.py`. Content flows naturally across pages
when it exceeds a single half-sheet.

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
```

### Step 3: Clean Up

Remove the temporary plan JSON file if it was created just for this step.

## Configuration

- Requires Python 3.7+, `jinja2`, `playwright`, and `pypdf`
- Playwright Chromium must be installed: `python -m playwright install chromium`
- `pypdf` is used for booklet imposition (saddle-stitch page ordering)
- Template is in `templates/booklet.html.j2` — edit to customize layout and styling
- The HTML uses `@media screen` for mobile and `@media print` for the PDF booklet
- No API keys required
