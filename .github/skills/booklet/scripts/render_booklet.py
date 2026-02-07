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
    """Render the plan data to an HTML string using the Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template("booklet.html.j2")
    return template.render(data)


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

    # Pad to a multiple of 4 (required for book fold)
    padded = n + ((4 - n % 4) % 4)

    # Build the page-pair list for booklet imposition.
    # For a saddle-stitch booklet printed duplex:
    #   Sheet 1 front: last, first     |  Sheet 1 back:  second, second-to-last
    #   Sheet 2 front: ...             |  ...
    # Each sheet has a front side (left=even-position, right=odd-position in sequence)
    # and a back side.
    pairs = []
    for i in range(padded // 2):
        # Booklet pairs: (padded-1-i, i) alternating left/right
        left = padded - 1 - i
        right = i
        pairs.append((left, right))

    # Reorder pairs so fronts and backs alternate for duplex printing:
    # Sheet 0 front = pairs[0], Sheet 0 back = pairs[1],
    # Sheet 1 front = pairs[2], Sheet 1 back = pairs[3], ...
    # This is already correct from the loop above when we process them
    # in order — each pair represents one side of one sheet.

    writer = PdfWriter()
    for left_idx, right_idx in pairs:
        spread = PageObject.create_blank_page(width=FULL_W, height=HALF_H)
        spread.mediabox = RectangleObject([0, 0, FULL_W, HALF_H])

        # Left half-page (placed at x=0)
        if left_idx < n:
            src_left = reader.pages[left_idx]
            spread.merge_transformed_page(
                src_left,
                Transformation().translate(tx=0, ty=0),
                over=True,
            )

        # Right half-page (placed at x=HALF_W)
        if right_idx < n:
            src_right = reader.pages[right_idx]
            spread.merge_transformed_page(
                src_right,
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

    print(f"OUTPUT_DIR={out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
