#!/usr/bin/env python3
"""Render a weekly plan JSON into a mobile-friendly HTML file and a PDF booklet.

Usage:
    python render_booklet.py plan_data.json
    python render_booklet.py plan_data.json -o weekly_plans/2026-02-08/
    python render_booklet.py plan_data.json --html-only
    python render_booklet.py plan_data.json --pdf-only
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def get_week_date(data):
    """Extract starting Sunday date from week_range for folder naming."""
    week_range = data.get("week_range", "")
    m = re.match(r"(\w+ \d+)\s*[–—-]\s*\w*\s*\d+,?\s*(\d{4})", week_range)
    if m:
        try:
            start_date = datetime.strptime(f"{m.group(1)}, {m.group(2)}", "%B %d, %Y")
            return start_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")


# Curated wisdom quotes for the cover page. Chosen for warmth, brevity,
# and applicability to family/weekly-rhythm life. One is selected per week
# deterministically from the week_start date so the same week always renders
# the same quote and consecutive weeks rotate predictably.
COVER_WISDOM = [
    ("Tell me, what is it you plan to do with your one wild and precious life?", "Mary Oliver"),
    ("We do not remember days, we remember moments.", "Cesare Pavese"),
    ("The days are long, but the years are short.", "Gretchen Rubin"),
    ("Attention is the rarest and purest form of generosity.", "Simone Weil"),
    ("Enough is a feast.", "Buddhist proverb"),
    ("How we spend our days is, of course, how we spend our lives.", "Annie Dillard"),
    ("The privilege of a lifetime is to become who you truly are.", "Carl Jung"),
    ("Be kind, for everyone you meet is fighting a hard battle.", "Ian Maclaren"),
    ("It is not length of life, but depth of life.", "Ralph Waldo Emerson"),
    ("Joy is the simplest form of gratitude.", "Karl Barth"),
    ("What we plant in the soil of contemplation, we shall reap in the harvest of action.", "Meister Eckhart"),
    ("To pay attention, this is our endless and proper work.", "Mary Oliver"),
    ("Almost everything will work again if you unplug it for a few minutes, including you.", "Anne Lamott"),
    ("The most important thing in communication is hearing what isn't said.", "Peter Drucker"),
    ("You are what you do, not what you say you'll do.", "Carl Jung"),
    ("Comparison is the thief of joy.", "Theodore Roosevelt"),
    ("We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "Will Durant"),
    ("Do small things with great love.", "Mother Teresa"),
    ("The opposite of play is not work — it is depression.", "Brian Sutton-Smith"),
    ("Wherever you are, be all there.", "Jim Elliot"),
    ("A house is made of walls and beams; a home is built with love and dreams.", "Ralph Waldo Emerson"),
    ("Tend the garden you can reach.", "Voltaire (paraphrased)"),
    ("Patience is bitter, but its fruit is sweet.", "Aristotle"),
    ("Slow is smooth, and smooth is fast.", "Navy SEAL adage"),
    ("Do not wait for the last judgment. It takes place every day.", "Albert Camus"),
    ("The cure for anything is salt water — sweat, tears, or the sea.", "Isak Dinesen"),
    ("Gratitude turns what we have into enough.", "Aesop"),
    ("There is no remedy for love but to love more.", "Henry David Thoreau"),
    ("Begin again. Always begin again.", "St. Benedict (paraphrased)"),
    ("The present moment always will have been.", "Kate Atkinson"),
]


def _select_wisdom(seed):
    """Pick a stable cover quote from COVER_WISDOM based on a seed string."""
    if not COVER_WISDOM:
        return ""
    if not seed:
        return f"\u201c{COVER_WISDOM[0][0]}\u201d \u2014 {COVER_WISDOM[0][1]}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(COVER_WISDOM)
    quote, author = COVER_WISDOM[idx]
    return f"\u201c{quote}\u201d \u2014 {author}"


def derive_highlight(data):
    """Generate a cover highlight from the plan data.

    Priority order:
      1. Explicit ``highlight`` field in the plan data (user override).
      2. A piece of wisdom — either pulled from principles/stoic theme content
         already in the plan, or selected from a curated rotating quote pool.

    The cover intentionally does NOT walk through the week's dinners; the
    Week at a Glance page already does that.
    """
    if data.get("highlight"):
        return data["highlight"]

    principles = data.get("principles_data") or {}
    principles_theme = principles.get("theme_quote") or principles.get("quote")
    if principles_theme:
        return principles_theme

    stoic = data.get("stoic_data") or {}
    stoic_quote = stoic.get("anchor_quote") or stoic.get("quote")
    if stoic_quote:
        return stoic_quote

    seed = data.get("week_start") or data.get("week_range") or ""
    return _select_wisdom(seed)


def render_html(data, template_dir):
    """Render the plan data to an HTML string using the Jinja2 template.

    Expects normalized fields (weather_oneliner, engagements, album_artist,
    album_title, dinner_question) from assemble_plan.py.  Uses
    parsed_engagements as an alias for engagements (print template compat).
    """
    # Ensure backward-compat aliases for templates
    for d in data.get("days", []):
        if "engagements" in d and "parsed_engagements" not in d:
            d["parsed_engagements"] = [
                {"time": e.get("time", ""), "event": e.get("event_short", e.get("event", ""))}
                for e in d["engagements"]
            ]

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("booklet.html.j2")
    return template.render(data)


def check_overflow(html_path):
    """Detect which booklet pages have content that overflows a single A5 page.

    Opens the HTML in a headless Chromium browser at print dimensions
    (148mm × 210mm / A5) and uses JavaScript to compare each .page element's
    scrollHeight against the available page height.  Returns a list of dicts
    describing each overflowing page.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    file_url = html_path.resolve().as_uri()

    # A5 page height in CSS px at 96 dpi: 210mm ≈ 8.27in → 8.27 * 96 ≈ 794
    # Margins: top 0.25in (24) + bottom 0.3in (28.8) ≈ 53
    # Available content height ≈ 741 CSS px
    PAGE_HEIGHT_PX = 794
    MARGIN_PX = 53   # top 0.25in + bottom 0.3in from @page rule
    CONTENT_HEIGHT_PX = PAGE_HEIGHT_PX - MARGIN_PX  # ~741

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 559, "height": PAGE_HEIGHT_PX},  # 148mm ≈ 5.83in * 96dpi ≈ 559
        )
        # Inject print media emulation so the .page divs become visible
        page.emulate_media(media="print")
        page.goto(file_url, wait_until="networkidle")

        # Query each .page element for its scroll height
        results = page.evaluate("""() => {
            const pages = document.querySelectorAll('.page');
            const info = [];
            for (let i = 0; i < pages.length; i++) {
                const el = pages[i];
                const classes = el.className;
                // Find the day header text if it's a day page
                let label = '';
                const h2 = el.querySelector('.section-header, .divider-title');
                if (h2) label = h2.textContent.trim();
                else {
                    const h1 = el.querySelector('h1');
                    if (h1) label = h1.textContent.trim();
                }
                info.push({
                    index: i,
                    label: label,
                    classes: classes,
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                });
            }
            return info;
        }""")
        browser.close()

    overflows = []
    for p_info in results:
        scroll_h = p_info["scrollHeight"]
        # Flag if the content exceeds the available page content area
        if scroll_h > CONTENT_HEIGHT_PX:
            overflows.append({
                "page_index": p_info["index"],
                "label": p_info["label"],
                "classes": p_info["classes"],
                "scroll_height": scroll_h,
                "available_height": CONTENT_HEIGHT_PX,
                "overflow_px": scroll_h - CONTENT_HEIGHT_PX,
                "is_day_page": "page-day" in p_info["classes"],
            })

    return overflows


def html_to_pdf(html_path, pdf_path):
    """Convert an HTML file to a PDF with individual A5 pages in reading order.

    Renders each logical page at A5 size (148mm × 210mm) via Playwright.
    Pages are output sequentially — no booklet imposition or book fold.
    Adobe Reader (or any PDF viewer) handles duplex/booklet printing.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            width="148mm",
            height="210mm",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    # Count pages for the summary message
    try:
        from pypdf import PdfReader
        n = len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        n = "?"
    print(f"PDF generated: {n} A5 pages in reading order",
          file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Render weekly plan as HTML and PDF booklet"
    )
    parser.add_argument(
        "input",
        help="Path to the plan JSON data file",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: weekly_plans/<YYYY-MM-DD>/)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Generate only the HTML file, skip PDF",
    )
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Generate only the PDF file, skip HTML",
    )
    parser.add_argument(
        "--extra-sections",
        help="Path to a JSON file with additional sections to append. "
             "Format: [{\"title\": \"...\", \"content\": \"...\"}]",
    )
    parser.add_argument(
        "--check-overflow",
        action="store_true",
        help="After rendering, check if any pages overflow their bounds and "
             "report which pages need shorter content. Exits with code 1 if "
             "any day pages overflow.",
    )
    parser.add_argument(
        "--parenting",
        help="Path to a JSON file with parenting data for the native parenting section. "
             "Generated by the parenting-coach skill.",
    )
    args = parser.parse_args()

    # Load plan data
    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # Inject defaults
    if "generated_at" not in data:
        data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not data.get("highlight"):
        data["highlight"] = derive_highlight(data)

    # Load extra sections if provided
    if args.extra_sections:
        with open(args.extra_sections, "r", encoding="utf-8-sig") as f:
            extras = json.load(f)
        existing = data.get("extra_sections", [])
        data["extra_sections"] = existing + extras

    # Load parenting data if provided
    if args.parenting:
        with open(args.parenting, "r", encoding="utf-8-sig") as f:
            data["parenting_data"] = json.load(f)

    # Determine output directory
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        week_date = get_week_date(data)
        out_dir = Path("weekly_plans") / week_date
    out_dir.mkdir(parents=True, exist_ok=True)

    # Locate template directory
    template_dir = Path(__file__).resolve().parent.parent / "templates"

    # Render HTML
    html_content = render_html(data, template_dir)

    # Always write HTML (needed for PDF generation too)
    html_path = out_dir / "weekly-plan.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    if not args.pdf_only:
        print(f"HTML written to {html_path}", file=sys.stderr)

    if not args.html_only:
        pdf_path = out_dir / "weekly-plan.pdf"
        print("Generating PDF booklet...", file=sys.stderr)
        html_to_pdf(html_path, pdf_path)
        print(f"PDF written to {pdf_path}", file=sys.stderr)
        # Remove HTML if pdf-only was requested
        if args.pdf_only:
            html_path.unlink()

    # Overflow check — always run when requested, otherwise skip
    if args.check_overflow:
        print("Checking for page overflow...", file=sys.stderr)
        overflows = check_overflow(html_path if html_path.exists() else out_dir / "weekly-plan.html")
        day_overflows = [o for o in overflows if o["is_day_page"]]
        if day_overflows:
            print(f"OVERFLOW: {len(day_overflows)} day page(s) exceed their bounds:",
                  file=sys.stderr)
            for o in day_overflows:
                print(f"  Page {o['page_index']}: \"{o['label']}\" — "
                      f"{o['overflow_px']}px over "
                      f"(content {o['scroll_height']}px, "
                      f"available {o['available_height']}px)",
                      file=sys.stderr)
            # Print as structured output for programmatic consumption
            overflow_json = json.dumps(day_overflows, indent=2)
            print(f"OVERFLOW_PAGES={overflow_json}")
            sys.exit(1)
        else:
            non_day = [o for o in overflows if not o["is_day_page"]]
            if non_day:
                print(f"NOTE: {len(non_day)} non-day page(s) overflow (support pages may span multiple pages by design).",
                      file=sys.stderr)
            print("OK: All day pages fit within their bounds.", file=sys.stderr)
            print("OVERFLOW_PAGES=[]")

    print(f"OUTPUT_DIR={out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
