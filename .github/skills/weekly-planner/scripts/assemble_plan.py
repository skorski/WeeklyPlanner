#!/usr/bin/env python3
"""Assemble a complete plan_data.json from individual skill outputs.

This script merges the core days configuration with supporting data files
produced by other skills (elevations, parenting, nutrition, etc.) into the
final plan_data.json that the build_plan.py renderer and booklet expect.

Typical usage:
    python assemble_plan.py days.json -o plan_data.json \
        --elevations elevations.json \
        --parenting parenting.json \
        --nutrition nutrition.json

The days.json file must contain the top-level plan structure including
a "days" array and optionally appetizers, salads, beverages, grocery_list,
prep_ahead, and notes.  Supporting files are merged in as follows:

  --elevations   Matched by dinner name into each day's dinner_elevation_tips
  --parenting    Stored as top-level parenting_data
  --nutrition    nutrition.weekly_nutrition_summary stored as nutrition_summary;
                 full object available for future template use
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Weather helpers ──────────────────────────────────────────────────────────

WEATHER_ICONS = [
    ("snow", "❄️"), ("rain", "🌧️"), ("shower", "🌧️"),
    ("cloud", "☁️"), ("overcast", "☁️"), ("partly", "⛅"),
    ("sun", "☀️"), ("clear", "☀️"),
]

_TEMP_RE = re.compile(r"(\d+)\s*°?\s*F?\s*/\s*(\d+)\s*°?\s*F?", re.IGNORECASE)
_GUST_RE = re.compile(r"gusts?\s*(\d+)", re.IGNORECASE)
_PRECIP_RE = re.compile(r"(\d+)%\s*precip", re.IGNORECASE)
_TIME_RE = re.compile(
    r"(\d{1,2}:\d{2}(?:\s*-\s*\d{1,2}:\d{2})?\s*[AP]M)", re.IGNORECASE
)
_PERIOD_RE = re.compile(r"\((evening|morning|afternoon|night)\)", re.IGNORECASE)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_ALBUM_SEPS = [" – ", " — ", " - "]
_DOW_MAP = {
    "sun": "sunday", "mon": "monday", "tue": "tuesday", "wed": "wednesday",
    "thu": "thursday", "fri": "friday", "sat": "saturday",
}


def _weather_icon(weather: str) -> str:
    w = weather.lower()
    for keyword, icon in WEATHER_ICONS:
        if keyword in w:
            return icon
    return "🌤️"


def _weather_condition(weather: str) -> str:
    w = weather.lower()
    for label, cond in [
        ("snow", "SNOW"), ("rain", "RAIN"), ("shower", "RAIN"),
        ("overcast", "OVERCAST"), ("cloud", "CLOUDY"),
        ("partly", "PARTLY CLOUDY"), ("clear", "CLEAR"), ("sun", "SUNNY"),
    ]:
        if label in w:
            return cond
    return weather.split(",")[0].strip().upper() if weather else ""


def normalize_weather(days: list) -> None:
    """Add structured weather fields to each day."""
    highs = []
    for d in days:
        m = _TEMP_RE.search(d.get("weather", ""))
        high = int(m.group(1)) if m else None
        low = int(m.group(2)) if m else None
        d["weather_high"] = high
        d["weather_low"] = low
        highs.append(high)

    valid = [h for h in highs if h is not None]
    max_h = max(valid) if valid else 0
    min_h = min(valid) if valid else 0
    spread = max_h - min_h

    for i, d in enumerate(days):
        w = d.get("weather", "")
        detail = (d.get("weather_detail", "") or "").lower()

        d["weather_condition"] = _weather_condition(w)
        d["weather_emoji"] = _weather_icon(w)

        # Build contextual one-liner
        high, low = d.get("weather_high"), d.get("weather_low")
        temp = f"{high}°/{low}°" if high is not None and low is not None else ""
        notes = []
        if high is not None and spread >= 5:
            if high == max_h:
                notes.append("warmest day")
            if high == min_h:
                notes.append("coldest day")
        if "bitter" in detail:
            notes.append("bitter cold")
        if "clearest" in detail:
            notes.append("clearest day")
        gm = _GUST_RE.search(detail)
        if gm and int(gm.group(1)) >= 30:
            notes.append("gusty")
        pm = _PRECIP_RE.search(detail)
        if pm:
            pv = int(pm.group(1))
            if pv >= 60:
                notes.append("likely rain")
            elif pv >= 30:
                notes.append("chance of rain")
        ctx = " · " + ", ".join(notes) if notes else ""
        d["weather_oneliner"] = f"{temp}{ctx}".strip()


# ── Engagement helpers ───────────────────────────────────────────────────────

def normalize_engagements(days: list) -> None:
    """Parse calendar_items into structured {time, event, event_short}."""
    for d in days:
        parsed = []
        for item in d.get("calendar_items", []):
            tm_match = _TIME_RE.search(item)
            if tm_match:
                t = tm_match.group(1).upper()
                ev = item[:tm_match.start()] + item[tm_match.end():]
                ev = re.sub(r"^\s*[,\-·]\s*", "", ev).strip()
                ev = re.sub(r"\s*\(\s*\)\s*", "", ev).strip()
            else:
                pm_match = _PERIOD_RE.search(item)
                if pm_match:
                    t = pm_match.group(1).upper()
                    ev = item[:pm_match.start()] + item[pm_match.end():]
                    ev = ev.strip()
                else:
                    t = ""
                    ev = item.strip()
            ev_short = _PAREN_RE.sub("", ev).strip() or ev
            parsed.append({"time": t, "event": ev, "event_short": ev_short})
        d["engagements"] = parsed


# ── Album helpers ────────────────────────────────────────────────────────────

def normalize_albums(days: list) -> None:
    """Split 'Artist – Title' into album_artist and album_title."""
    for d in days:
        album = d.get("album", "")
        if d.get("album_artist") and d.get("album_title"):
            continue  # already set
        if not album:
            d.setdefault("album_artist", "")
            d.setdefault("album_title", "")
            continue
        for sep in _ALBUM_SEPS:
            if sep in album:
                parts = album.split(sep, 1)
                d["album_artist"] = parts[0].strip()
                d["album_title"] = parts[1].strip()
                break
        else:
            d["album_artist"] = ""
            d["album_title"] = album


# ── Day-of-week helpers ─────────────────────────────────────────────────────

def normalize_day_of_week(days: list) -> None:
    """Add day_of_week ('sunday', 'monday', ...) to each day."""
    for d in days:
        long_n = (d.get("long_name") or "").split(",")[0].strip().lower()
        if long_n:
            d["day_of_week"] = long_n
            continue
        short = (d.get("name") or "").split()[0].strip().lower()
        d["day_of_week"] = _DOW_MAP.get(short, short)


# ── Section subtitle helpers ─────────────────────────────────────────────────

def generate_section_subtitles(data: dict) -> None:
    """Generate short subtitles for section dividers from the week's content.

    These are starting points — the final-editor skill should polish them
    into something witty and specific to the week.
    """
    days = data.get("days", [])
    if data.get("daily_plan_subtitle"):
        return  # already set (e.g., by the final-editor)

    cuisines = list(dict.fromkeys(
        d.get("dinner_cuisine", "") for d in days if d.get("dinner_cuisine")
    ))
    dinners = [d.get("dinner", "") for d in days if d.get("dinner")]
    artists = [d.get("album_artist", "") for d in days if d.get("album_artist")]

    if len(cuisines) >= 3:
        data["daily_plan_subtitle"] = (
            f"From {cuisines[0]} to {cuisines[-1]}, "
            f"with {artists[0]} on the stereo" if artists
            else f"From {cuisines[0]} to {cuisines[-1]}, seven nights at the table"
        )
    elif dinners and artists:
        data["daily_plan_subtitle"] = (
            f"{dinners[0]}, {artists[0]}, and everything in between"
        )
    else:
        data["daily_plan_subtitle"] = "Seven days of dinner, music, and good company"


def get_week_folder(data):
    """Derive the weekly_plans/<YYYY-MM-DD> folder from the plan data."""
    week_range = data.get("week_range", "")
    m = re.match(r"(\w+ \d+)\s*[–—-]\s*\w*\s*\d+,?\s*(\d{4})", week_range)
    if m:
        try:
            start_date = datetime.strptime(f"{m.group(1)}, {m.group(2)}", "%B %d, %Y")
            return start_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def merge_elevations(data, elevations):
    """Match elevation tips to days by dinner name."""
    elev_map = {}
    for e in elevations:
        name = e.get("name", "")
        tips = e.get("elevations", [])
        elev_map[name] = tips
        # Also index by lowercase for fuzzy matching
        elev_map[name.lower()] = tips

    merged_count = 0
    for day in data.get("days", []):
        dinner = day.get("dinner", "")
        tips = elev_map.get(dinner) or elev_map.get(dinner.lower(), [])
        if tips:
            day["dinner_elevation_tips"] = tips
            merged_count += 1
        elif "dinner_elevation_tips" not in day:
            day["dinner_elevation_tips"] = []

    return merged_count


def merge_parenting(data, parenting):
    """Store parenting data at top level and map dinner questions onto days."""
    data["parenting_data"] = parenting
    # Map dinner questions onto each day by day_of_week
    dq_map = {}
    for q in parenting.get("dinner_questions", []):
        day_name = (q.get("day") or "").strip().lower()
        if day_name:
            dq_map[day_name] = q
    for d in data.get("days", []):
        dow = d.get("day_of_week", "")
        dq = dq_map.get(dow)
        if not dq:
            # Fallback: prefix match
            for key, val in dq_map.items():
                if key.startswith(dow[:3]) or dow.startswith(key[:3]):
                    dq = val
                    break
        d["dinner_question"] = dq


def merge_nutrition(data, nutrition):
    """Extract nutrition summary and store the full analysis."""
    summary = nutrition.get("weekly_nutrition_summary", "")
    if summary:
        data["nutrition_summary"] = summary
    # Store full analysis for templates that want deeper access
    data["nutrition_data"] = nutrition


def main():
    parser = argparse.ArgumentParser(
        description="Assemble plan_data.json from skill outputs"
    )
    parser.add_argument(
        "input",
        help="Path to the core days JSON file containing the plan structure "
             "(must have at minimum a 'days' array and 'week_range')",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for the assembled plan_data.json. "
             "Default: weekly_plans/<date>/plan_data.json",
    )
    parser.add_argument(
        "--elevations",
        help="Path to elevations JSON from the dinner-designer skill. "
             "Each entry is matched to a day by dinner name.",
    )
    parser.add_argument(
        "--parenting",
        help="Path to parenting JSON from the parenting-coach skill.",
    )
    parser.add_argument(
        "--nutrition",
        help="Path to nutrition JSON from the nutrition-coach skill.",
    )
    parser.add_argument(
        "--newsletter",
        help="Path to newsletter JSON from the linkwarden skill.",
    )
    parser.add_argument(
        "--stoic",
        help="Path to stoic guide JSON from the stoic-guide skill.",
    )
    parser.add_argument(
        "--child-wisdom",
        help="Path to child-wisdom JSON from the child-wisdom skill.",
    )
    args = parser.parse_args()

    # Load core plan data
    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if "days" not in data:
        print("ERROR: Input JSON must contain a 'days' array", file=sys.stderr)
        sys.exit(1)

    # Inject generation timestamp
    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Normalize structured fields on each day ──
    days = data["days"]
    normalize_day_of_week(days)
    normalize_weather(days)
    normalize_albums(days)
    normalize_engagements(days)
    generate_section_subtitles(data)
    print(f"Normalized: weather, albums, engagements, day_of_week, subtitles", file=sys.stderr)

    # Merge elevations
    if args.elevations:
        with open(args.elevations, "r", encoding="utf-8-sig") as f:
            elevations = json.load(f)
        count = merge_elevations(data, elevations)
        print(f"Merged elevations: {count}/{len(data['days'])} days matched",
              file=sys.stderr)

    # Merge parenting
    if args.parenting:
        with open(args.parenting, "r", encoding="utf-8-sig") as f:
            parenting = json.load(f)
        merge_parenting(data, parenting)
        print("Merged parenting data", file=sys.stderr)

    # Merge nutrition
    if args.nutrition:
        with open(args.nutrition, "r", encoding="utf-8-sig") as f:
            nutrition = json.load(f)
        merge_nutrition(data, nutrition)
        print("Merged nutrition data", file=sys.stderr)

    # Merge newsletter
    if args.newsletter:
        with open(args.newsletter, "r", encoding="utf-8-sig") as f:
            newsletter = json.load(f)
        data["newsletter_data"] = newsletter
        article_count = len(newsletter.get("clusters", []))
        print(f"Merged newsletter data: {article_count} clusters", file=sys.stderr)

    # Merge stoic guide
    if args.stoic:
        with open(args.stoic, "r", encoding="utf-8-sig") as f:
            stoic = json.load(f)
        data["stoic_data"] = stoic
        print("Merged stoic guide data", file=sys.stderr)

    # Merge child wisdom story
    if getattr(args, 'child_wisdom', None):
        with open(args.child_wisdom, "r", encoding="utf-8-sig") as f:
            data["child_wisdom"] = json.load(f)
        print("Merged child wisdom story", file=sys.stderr)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        week_date = get_week_folder(data)
        out_dir = Path("weekly_plans") / week_date
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "plan_data.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write assembled plan
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    days_count = len(data.get("days", []))
    appetizers = len(data.get("appetizers", []))
    salads = len(data.get("salads", []))
    beverages = len(data.get("beverages", []))
    has_parenting = "parenting_data" in data
    has_nutrition = "nutrition_summary" in data
    has_elevations = any(
        d.get("dinner_elevation_tips") for d in data.get("days", [])
    )
    has_newsletter = "newsletter_data" in data
    has_stoic = "stoic_data" in data

    print(f"Plan assembled: {days_count} days, {appetizers} appetizers, "
          f"{salads} salads, {beverages} beverages", file=sys.stderr)
    print(f"  Parenting: {'✓' if has_parenting else '✗'}  "
          f"Nutrition: {'✓' if has_nutrition else '✗'}  "
          f"Elevations: {'✓' if has_elevations else '✗'}  "
          f"Newsletter: {'✓' if has_newsletter else '✗'}  "
          f"Stoic: {'✓' if has_stoic else '✗'}", file=sys.stderr)
    print(f"Written to {out_path}", file=sys.stderr)
    print(f"PLAN_DATA={out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
