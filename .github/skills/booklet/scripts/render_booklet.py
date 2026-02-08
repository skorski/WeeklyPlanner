#!/usr/bin/env python3
"""Render a weekly plan JSON into a mobile-friendly HTML file and a PDF booklet.

Usage:
    python render_booklet.py plan_data.json
    python render_booklet.py plan_data.json -o weekly_plans/2026-02-08/
    python render_booklet.py plan_data.json --html-only
    python render_booklet.py plan_data.json --pdf-only
"""

import argparse
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


def derive_highlight(data):
    """Generate a cover highlight from the plan data if not provided."""
    if data.get("highlight"):
        return data["highlight"]

    days = data.get("days", [])
    highlights = []
    for day in days:
        long_name = day.get("long_name", "")
        if "Valentine" in long_name:
            dinner = day.get("dinner", "")
            highlights.append(f"Valentine's Day — {dinner}" if dinner else "Valentine's Day")
        elif "Super Bowl" in long_name:
            dinner = day.get("dinner", "")
            highlights.append(f"Super Bowl Sunday — {dinner}" if dinner else "Super Bowl Sunday")
        elif any("potluck" in (item or "").lower() for item in day.get("calendar_items", [])):
            highlights.append(f"Work Potluck — {day.get('dinner', 'TBD')}")

    if highlights:
        return " · ".join(highlights[:2])
    # Fallback: first and last dinner
    if len(days) >= 2:
        return f"{days[0].get('dinner', '?')} → {days[-1].get('dinner', '?')}"
    return ""


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
    """Detect which booklet pages have content that overflows a single half-letter page.

    Opens the HTML in a headless Chromium browser at print dimensions (5.5" × 8.5")
    and uses JavaScript to compare each .page element's scrollHeight against the
    available page height.  Returns a list of dicts describing each overflowing page.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    file_url = html_path.resolve().as_uri()

    # Page height in CSS px at 96 dpi: 8.5 * 96 = 816
    # Margins: top 0.5in (48) + bottom 0.55in (52.8) = 100.8
    # Available content height ≈ 715 CSS px
    PAGE_HEIGHT_PX = 816
    MARGIN_PX = 53   # top 0.25in + bottom 0.3in from @page rule
    CONTENT_HEIGHT_PX = PAGE_HEIGHT_PX - MARGIN_PX  # ~763

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 528, "height": PAGE_HEIGHT_PX},  # 5.5in * 96dpi
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
    """Convert an HTML file to a saddle-stitch booklet PDF.

    1. Render each logical page at 5.5" × 8.5" (half-letter) via Playwright.
    2. Impose two half-pages side-by-side on 11" × 8.5" (letter landscape)
       in booklet signature order so the output can be printed duplex,
       stacked, and folded once in the center.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed. Run: pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    try:
        from pypdf import PdfReader, PdfWriter, PageObject, Transformation
        from pypdf.generic import RectangleObject
    except ImportError:
        print("ERROR: pypdf is not installed. Run: pip install pypdf",
              file=sys.stderr)
        sys.exit(1)

    # Step 1: Render half-letter pages (5.5 × 8.5 in, matching CSS @page)
    HALF_W = 5.5 * 72   # 396 pt
    HALF_H = 8.5 * 72   # 612 pt
    FULL_W = 11 * 72    # 792 pt  (letter landscape width)

    tmp_pdf = pdf_path.with_name("_booklet_pages.pdf")
    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=str(tmp_pdf),
            width="5.5in",
            height="8.5in",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    # Step 2: Impose in booklet (saddle-stitch) order
    reader = PdfReader(str(tmp_pdf))
    n = len(reader.pages)

    # Pad to a multiple of 4 (required for book fold).
    # The back cover (last HTML page) must land on the very last padded
    # position so it prints on the physical back of the booklet.  We
    # build an ordered list of page indices where None = blank page,
    # moving the back-cover index from n-1 to padded-1.
    padded = n + ((4 - n % 4) % 4)
    page_order = list(range(n - 1))          # all pages except back cover
    page_order += [None] * (padded - n)      # blank padding pages
    page_order.append(n - 1)                 # back cover last

    # Build the page-pair list for booklet imposition.
    # For a saddle-stitch booklet printed duplex:
    #   Sheet 1 front: last, first     |  Sheet 1 back:  second, second-to-last
    #   Sheet 2 front: ...             |  ...
    # Each sheet has a front side (left=even-position, right=odd-position in sequence)
    # and a back side.
    pairs = []
    for i in range(padded // 2):
        left = padded - 1 - i
        right = i
        pairs.append((left, right))

    writer = PdfWriter()
    for left_idx, right_idx in pairs:
        spread = PageObject.create_blank_page(width=FULL_W, height=HALF_H)
        spread.mediabox = RectangleObject([0, 0, FULL_W, HALF_H])

        # Left half-page (placed at x=0)
        left_page = page_order[left_idx] if left_idx < len(page_order) else None
        if left_page is not None:
            spread.merge_transformed_page(
                reader.pages[left_page],
                Transformation().translate(tx=0, ty=0),
                over=True,
            )

        # Right half-page (placed at x=HALF_W)
        right_page = page_order[right_idx] if right_idx < len(page_order) else None
        if right_page is not None:
            spread.merge_transformed_page(
                reader.pages[right_page],
                Transformation().translate(tx=HALF_W, ty=0),
                over=True,
            )

        writer.add_page(spread)

    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Clean up temp file
    tmp_pdf.unlink(missing_ok=True)
    print(f"Booklet imposed: {n} pages → {len(pairs)} sheets (print duplex, fold in center)",
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
