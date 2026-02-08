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

### 2. Content Completeness
Compares the rendered HTML against `plan_data.json` to verify:
- Every day's **dinner name** appears on a `page-day-left`
- Every day's **album title** appears on a `page-day-right`
- Every day's **chef's tips** titles appear on a `page-day-right`
- Every day's **conversation starter** appears on a `page-day-left`
- Every day's **weather one-liner** appears
- All **engagements** (calendar events) render on the correct day

### 3. Page Structure Validation
- Cover is page 1 (no page number)
- Week at a Glance is page 2
- Daily Plan divider is page 3 (no page number)
- Days are pages 4–17 (7 days × 2 pages each)
- Section dividers have no page numbers
- Back cover is the last page (no page number)
- Page numbers are sequential with no gaps

### 4. Text Truncation Detection
Checks for CSS `text-overflow: ellipsis` truncation in engagement rows
and other constrained elements by comparing rendered text width against
container width.

## Usage

```bash
python .github/skills/proofreader/scripts/proofread.py \
    weekly_plans/2026-02-08/plan_data.json \
    weekly_plans/2026-02-08/weekly-plan.html
```

**Options:**
```bash
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

OVERFLOW ............ PASS (0 day pages overflow)
CONTENT ............. PASS (7/7 dinners, 7/7 albums, 7/7 tips, 7/7 questions)
STRUCTURE ........... PASS (26 pages, correct section order)
PAGE NUMBERS ........ PASS (sequential 2-25, dividers hidden)
TRUNCATION .......... WARN (2 engagements truncated on Tuesday)

RESULT: PASS (1 warning)
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
