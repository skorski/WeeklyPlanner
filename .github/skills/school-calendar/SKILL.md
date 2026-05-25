---
name: school-calendar
category: researcher
description: >
  Look up Fairfax County Public Schools (FCPS) 2025-2026 school calendar for
  days off, half days, and early releases within a date range. Use this skill
  when building a weekly plan to check if Elsie has school closures, teacher
  workdays, staff development days, or early release days during the plan week.
  Triggers on weekly planner workflows, or when the user asks about school
  schedule, days off, or half days.
---

# FCPS School Calendar Lookup

Check the FCPS 2025-2026 standard school year calendar for days off and early
releases within a given week. The calendar data is pre-parsed from the
[official PDF](https://www.fcps.edu/system/files/forms/2024-02/2025-2026-standard-school-year-calendar.pdf)
and stored in `references/fcps_2025_2026.json`.

## Usage

```bash
python scripts/lookup_school_calendar.py --start YYYY-MM-DD --end YYYY-MM-DD [-o output.json]
```

The script returns JSON with two arrays:
- `no_school` — full days off (holidays, teacher workdays, staff development)
- `early_release` — half days (quarter ends, last day of school)

Each entry has `date`, `reason`, and `type` fields.

## Integration with Weekly Planner

When the weekly-planner skill runs, invoke this skill early (alongside weather)
to get school events for the plan week. Then:

1. Add any **no-school days** to the day's `calendar_items` array
   (e.g., "No School — Thanksgiving Break")
2. Add any **early release days** to `calendar_items`
   (e.g., "Early Release — End of Quarter 1")
3. Factor school closures into dinner planning — a day off means Elsie is home
   all day, which may affect meal timing or complexity

## Output Contract

The content-validator checks this output before assembly.

```json
{
  "no_school": ["YYYY-MM-DD — Reason"],
  "early_release": ["YYYY-MM-DD — Reason"]
}
```

### Validation Rules
- Both `no_school` and `early_release` must be arrays (may be empty)
- Each entry is a string with date and reason separated by ` — `
- Dates must fall within the requested week range

## Updating the Calendar

The reference data lives in `references/fcps_2025_2026.json`. To update for a
new school year, download the new PDF from fcps.edu and re-parse the dates into
the same JSON format.

### Sources to cross-check when refreshing

The official FCPS PDF sometimes omits or under-labels student holidays (for
example, religious observances like **Eid al-Adha** or single teacher workdays
adjacent to a federal holiday). When refreshing the reference data, cross-check
all of the following before publishing:

1. **Official PDF** — `https://www.fcps.edu/calendars` (download the standard
   school-year calendar PDF).
2. **FCPS revised calendar listings** — published mid-year corrections.
3. **Religious & cultural observance dates** — Eid al-Fitr, Eid al-Adha,
   Diwali, Lunar New Year, Yom Kippur, Rosh Hashanah, Orthodox Christmas. FCPS
   marks many of these as student holidays.
4. **Teacher workdays adjacent to federal holidays** — FCPS frequently
   schedules a workday the day after Memorial Day or around Presidents' Day.

If a single source disagrees with the master PDF, prefer the most recent
revised calendar from FCPS, not the original publication.

### Validation script

After editing `references/fcps_2025_2026.json`, smoke-test the lookup against a
week you know has off-days to confirm the parser sees them:

```bash
python scripts/lookup_school_calendar.py --start 2026-05-24 --end 2026-05-30
```

The output should include Memorial Day **and** any adjacent teacher workdays
or religious holidays in that week.

