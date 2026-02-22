---
name: proofreader
description: >
  Proofread and validate a rendered weekly plan booklet. Checks the HTML for
  page overflow, verifies all plan content (dinners, albums, chef's tips,
  conversation starters, events) appears on the correct pages, validates page
  numbering sequence, and confirms section order. Use this skill after the
  booklet skill has produced its HTML and PDF. Triggers on requests to
  "proofread the booklet," "validate the PDF," "check the print layout,"
  or "QA the plan."
---

# Booklet Proofreader

Validate a rendered weekly plan booklet for correctness, completeness, and
layout integrity. This skill runs **after** the booklet skill has produced
`weekly-plan.html` and `weekly-plan.pdf`.

## What It Checks

### 1. Page Overflow Detection
Opens the HTML in headless Chromium at print dimensions (5.5" × 8.5") and
measures every `.page` element's `scrollHeight` vs the available content
area (715 CSS px). Reports any page that bleeds past its boundary.

### 2. Field Shape Validation
Validates that `plan_data.json` fields match the exact types expected by the
Jinja2 booklet templates. Catches mismatches that silently produce blank
sections:
- `dinner_question` must be a dict `{question, why}`, not a plain string
- `dinner_elevation_tips[]` must be dicts `{type, title, instruction}`, not strings
- `recipe_card` must be a dict `{nonna_says, engineer_table, variations}`, not None — recipe pages will be blank if missing
- `stoic_data` must use `theme` (dict) and `meditations[]`, not `weekly_theme`/`days`
- `principles_data` must use `daily_entries[]` and `theme` (dict), not `days`/`weekly_theme`
- `parenting_data` must use `dinner_questions[]`, not `days`

### 3. Content Completeness
Compares the rendered HTML against `plan_data.json` to verify:
- Every day's **dinner name** appears on a `page-day-left`
- Every day's **album title** appears on a `page-day-right`
- Every day's **chef's tips** titles appear on a `page-day-right`
- Every day's **conversation starter** appears on a `page-day-left`
- Every day's **weather one-liner** appears
- All **engagements** (calendar events) render on the correct day
- Every day's **recipe card** (nonna text) appears on a `page-day-recipe`

### 4. Page Structure Validation
- Cover is page 1 (no page number)
- Week at a Glance is page 2
- Daily Plan divider is page 3 (no page number)
- Days are pages 4–17 (7 days × 2 pages each)
- Section dividers have no page numbers
- Back cover is the last page (no page number)
- Page numbers are sequential with no gaps

### 5. Text Truncation Detection
Checks for CSS `text-overflow: ellipsis` truncation in engagement rows
and other constrained elements by comparing rendered text width against
container width.

### 6. Markdown Completeness
Validates the rendered markdown (`weekly-plan.md`) contains:
- Every day's dinner name, recipe directions (nonna says), chef's tips, and album
- Auto-detected from sibling file, or pass explicitly with `--md`

### 7. PDF Content Validation
Extracts text from the PDF (`weekly-plan.pdf`) via pypdf and verifies:
- Every day's dinner name, recipe directions, and chef's tips are present
- Reports total page count
- Auto-detected from sibling file, or pass explicitly with `--pdf`

## Usage

```bash
# Full validation of all three outputs (HTML, MD, PDF auto-detected)
python .github/skills/proofreader/scripts/proofread.py \
    weekly_plans/2026-02-08/plan_data.json \
    weekly_plans/2026-02-08/weekly-plan.html
```

**Options:**
```bash
# Explicit paths for markdown and PDF
python .github/skills/proofreader/scripts/proofread.py plan_data.json weekly-plan.html \
    --md weekly-plan.md --pdf weekly-plan.pdf

# Only check overflow (fast)
python .github/skills/proofreader/scripts/proofread.py plan_data.json weekly-plan.html --overflow-only

# Verbose output (show all checks, not just failures)
python .github/skills/proofreader/scripts/proofread.py plan_data.json weekly-plan.html --verbose

# JSON report output
python .github/skills/proofreader/scripts/proofread.py plan_data.json weekly-plan.html --json
```

## Output

Returns a structured report with pass/fail for each check:

```
PROOFREADER REPORT
==================

FIELD SHAPES ........ PASS (all fields match template contract)
OVERFLOW ............ PASS (0 day pages overflow)
CONTENT ............. PASS (7/7 dinners, 7/7 albums, 7/7 tips, 7/7 questions, 7/7 recipes)
STRUCTURE ........... PASS (42 pages, correct section order)
PAGE NUMBERS ........ PASS (sequential 2-31, dividers hidden)
TRUNCATION .......... PASS (no text truncated)
MARKDOWN ............ PASS (7/7 dinners, 7/7 recipes, 7/7 tips, 7/7 albums)
PDF CONTENT ......... PASS (7/7 dinners, 7/7 recipes, 7/7 tips, 42 pages)

RESULT: PASS
```

Exit codes:
- 0 = all checks pass (warnings allowed)
- 1 = one or more checks failed (content missing, overflow, wrong structure)

## Workflow

### Step 1: Locate Files
Find the `plan_data.json` and `weekly-plan.html` in the week folder.
Both are required — the JSON provides the source of truth, the HTML is
what gets validated.

### Step 2: Run Proofreader
```bash
python .github/skills/proofreader/scripts/proofread.py \
    weekly_plans/2026-02-08/plan_data.json \
    weekly_plans/2026-02-08/weekly-plan.html
```

### Step 3: Fix Issues
If the proofreader reports failures:
- **Overflow**: Reduce content length (use final-editor skill to trim copy)
- **Missing content**: Check plan_data.json has the field; check template renders it
- **Wrong structure**: Check print-days.j2 and print-cover.j2 page order
- **Truncation**: Shorten engagement text or increase column width

### Step 4: Re-validate
Run the proofreader again after fixes to confirm resolution.

## Configuration
- Requires Python 3.7+, `playwright`, `beautifulsoup4`
- Playwright Chromium must be installed
- No API keys required
