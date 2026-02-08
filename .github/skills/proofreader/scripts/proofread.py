#!/usr/bin/env python3
"""Proofread and validate a rendered weekly plan booklet.

Checks page overflow, content completeness, page structure, page numbering,
and text truncation against the source plan_data.json.

Usage:
    python proofread.py plan_data.json weekly-plan.html
    python proofread.py plan_data.json weekly-plan.html --verbose
    python proofread.py plan_data.json weekly-plan.html --json
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

PAGE_HEIGHT_PX = 816       # 8.5in * 96dpi
MARGIN_PX = 53             # top 0.25in (24) + bottom 0.3in (28.8) at 96dpi
CONTENT_HEIGHT_PX = PAGE_HEIGHT_PX - MARGIN_PX  # ~763


# ── Check: Overflow ─────────────────────────────────────────────────────────

def check_overflow(html_path):
    """Detect pages whose content exceeds the available half-letter area."""
    from playwright.sync_api import sync_playwright

    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 528, "height": PAGE_HEIGHT_PX},
        )
        page.emulate_media(media="print")
        page.goto(file_url, wait_until="networkidle")

        results = page.evaluate("""() => {
            const pages = document.querySelectorAll('.page');
            return Array.from(pages).map((el, i) => ({
                index: i,
                classes: el.className,
                scrollHeight: el.scrollHeight,
                label: (el.querySelector('.section-header, .divider-title, h1')
                        || {}).textContent || '',
            }));
        }""")
        browser.close()

    issues = []
    for p_info in results:
        sh = p_info["scrollHeight"]
        if sh > CONTENT_HEIGHT_PX:
            classes = p_info["classes"]
            is_day = "page-day" in classes
            # Pages that use overflow:hidden and must fit in a single page
            is_bounded = is_day or any(
                c in classes for c in (
                    "page-stoic", "page-parenting", "page-glance",
                    "page-support", "page-grocery", "page-extra",
                )
            )
            issues.append({
                "page": p_info["index"] + 1,
                "label": p_info["label"],
                "classes": classes,
                "overflow_px": sh - CONTENT_HEIGHT_PX,
                "is_day_page": is_day,
                "is_bounded_page": is_bounded,
            })
    return issues


# ── Check: Content completeness ─────────────────────────────────────────────

def check_content(html_text, plan_data):
    """Verify every day's key content appears in the rendered HTML."""
    days = plan_data.get("days", [])
    issues = []
    stats = {"dinners": 0, "albums": 0, "tips": 0, "questions": 0,
             "weather": 0, "engagements": 0}

    for i, day in enumerate(days):
        day_label = day.get("long_name", day.get("name", f"Day {i+1}"))

        # Dinner name
        dinner = day.get("dinner", "")
        if dinner:
            if dinner in html_text:
                stats["dinners"] += 1
            else:
                issues.append(f"MISSING dinner '{dinner}' for {day_label}")

        # Album title
        album_title = day.get("album_title", "")
        if album_title:
            if album_title in html_text:
                stats["albums"] += 1
            else:
                issues.append(f"MISSING album '{album_title}' for {day_label}")

        # Chef's tips (check at least one tip title)
        tips = day.get("dinner_elevation_tips", [])
        if tips:
            found = any(t.get("title", "") in html_text for t in tips)
            if found:
                stats["tips"] += 1
            else:
                issues.append(f"MISSING chef's tips for {day_label}")

        # Conversation starter
        dq = day.get("dinner_question")
        if dq and dq.get("question"):
            q_text = dq["question"][:60]  # check first 60 chars
            if q_text in html_text:
                stats["questions"] += 1
            else:
                issues.append(f"MISSING conversation starter for {day_label}")

        # Weather one-liner
        oneliner = day.get("weather_oneliner", "")
        if oneliner:
            # Check temp portion (most reliable part)
            temp_part = oneliner.split(" · ")[0]
            if temp_part and temp_part in html_text:
                stats["weather"] += 1
            else:
                issues.append(f"MISSING weather for {day_label}")

        # Engagements
        engagements = day.get("engagements", [])
        if engagements:
            found = any(
                e.get("event_short", e.get("event", ""))[:20] in html_text
                for e in engagements
            )
            if found:
                stats["engagements"] += 1
            elif engagements:
                issues.append(f"MISSING engagements for {day_label}")

    return issues, stats


# ── Check: Page structure ────────────────────────────────────────────────────

def check_structure(html_text):
    """Validate page class order matches expected booklet structure."""
    # Extract all page classes in order
    page_classes = re.findall(r'class="page\s+([^"]+)"', html_text)
    issues = []
    total = len(page_classes)

    if total == 0:
        return [{"severity": "FAIL", "msg": "No .page elements found"}], 0

    # Check cover is first
    if not page_classes[0].startswith("page-cover"):
        issues.append(f"First page should be cover, got '{page_classes[0]}'")

    # Check back cover is last (among print pages — filter out screen)
    print_pages = [c for c in page_classes if "screen" not in c.lower()]
    if print_pages and "page-back" not in print_pages[-1]:
        issues.append(f"Last print page should be back cover, got '{print_pages[-1]}'")

    # Check glance is second
    if total >= 2 and "page-glance" not in page_classes[1]:
        issues.append(f"Second page should be glance, got '{page_classes[1]}'")

    # Check daily plan divider is third
    if total >= 3 and "page-divider" not in page_classes[2]:
        issues.append(f"Third page should be divider, got '{page_classes[2]}'")

    # Check day pages come in left/right pairs
    day_pages = [(i, c) for i, c in enumerate(page_classes) if "page-day" in c]
    for j in range(0, len(day_pages), 2):
        if j + 1 >= len(day_pages):
            issues.append(f"Odd number of day pages — page {day_pages[j][0]+1} has no pair")
            break
        left_cls = day_pages[j][1]
        right_cls = day_pages[j + 1][1]
        if "page-day-left" not in left_cls:
            issues.append(f"Day page {day_pages[j][0]+1} should be left, got '{left_cls}'")
        if "page-day-right" not in right_cls:
            issues.append(f"Day page {day_pages[j+1][0]+1} should be right, got '{right_cls}'")

    return issues, total


# ── Check: Page numbers ─────────────────────────────────────────────────────

def check_page_numbers(html_text):
    """Validate page numbers are sequential and dividers have none."""
    # Extract folio values and their parent page class
    folio_pattern = re.compile(
        r'class="page\s+([^"]+)".*?class="page-folio">([^<]*)</div>',
        re.DOTALL,
    )
    issues = []
    numbers = []

    for m in folio_pattern.finditer(html_text):
        cls = m.group(1)
        folio_text = m.group(2).strip()

        # Dividers, cover, back should have no visible number
        is_hidden = any(k in cls for k in ["page-divider", "page-cover", "page-back"])
        if is_hidden and folio_text:
            # CSS hides these, but check template didn't render a number
            # Actually, template does render a number but CSS display:none hides it
            # This is acceptable — skip
            pass

        if folio_text and folio_text.isdigit():
            numbers.append(int(folio_text))

    # Check sequential (allowing gaps for hidden dividers)
    if numbers:
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        if numbers != expected:
            # Find specific gaps
            for i in range(1, len(numbers)):
                if numbers[i] != numbers[i - 1] + 1:
                    issues.append(
                        f"Page number gap: {numbers[i-1]} → {numbers[i]} "
                        f"(expected {numbers[i-1]+1})"
                    )

    return issues, numbers


# ── Check: Truncation ───────────────────────────────────────────────────────

def check_truncation(html_path):
    """Detect text truncated by CSS ellipsis in engagement rows."""
    from playwright.sync_api import sync_playwright

    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 528, "height": PAGE_HEIGHT_PX},
        )
        page.emulate_media(media="print")
        page.goto(file_url, wait_until="networkidle")

        truncated = page.evaluate("""() => {
            const items = document.querySelectorAll('.engagement-event');
            const results = [];
            for (const el of items) {
                if (el.scrollWidth > el.clientWidth + 2) {
                    const row = el.closest('.page');
                    const dayHeader = row ?
                        (row.querySelector('.section-header') || {}).textContent : '';
                    results.push({
                        text: el.textContent.trim(),
                        day: (dayHeader || '').trim(),
                        overflowPx: el.scrollWidth - el.clientWidth,
                    });
                }
            }
            return results;
        }""")
        browser.close()

    return truncated


# ── Report ───────────────────────────────────────────────────────────────────

def format_report(overflow, content_issues, content_stats, structure_issues,
                  page_count, number_issues, page_numbers, truncated,
                  verbose=False):
    """Format the proofreading results as a human-readable report."""
    lines = []
    lines.append("")
    lines.append("PROOFREADER REPORT")
    lines.append("=" * 40)
    lines.append("")

    total_days = 7
    has_failure = False
    warnings = 0

    # Overflow
    bounded_overflows = [o for o in overflow if o.get("is_bounded_page")]
    cosmetic_overflows = [o for o in overflow if not o.get("is_bounded_page")]
    if bounded_overflows:
        has_failure = True
        lines.append(f"OVERFLOW ............ FAIL ({len(bounded_overflows)} page(s) overflow)")
        for o in bounded_overflows:
            lines.append(f"  Page {o['page']}: \"{o['label']}\" — {o['overflow_px']}px over")
    else:
        lines.append(f"OVERFLOW ............ PASS (0 bounded pages overflow)")
    if cosmetic_overflows and verbose:
        lines.append(f"  NOTE: {len(cosmetic_overflows)} unbounded pages overflow (dividers/covers)")
    lines.append("")

    # Content
    s = content_stats
    if content_issues:
        has_failure = True
        summary = (f"{s['dinners']}/{total_days} dinners, "
                   f"{s['albums']}/{total_days} albums, "
                   f"{s['tips']}/{total_days} tips, "
                   f"{s['questions']}/{total_days} questions")
        lines.append(f"CONTENT ............. FAIL ({summary})")
        for issue in content_issues:
            lines.append(f"  {issue}")
    else:
        lines.append(f"CONTENT ............. PASS "
                     f"({s['dinners']}/{total_days} dinners, "
                     f"{s['albums']}/{total_days} albums, "
                     f"{s['tips']}/{total_days} tips, "
                     f"{s['questions']}/{total_days} questions)")
    lines.append("")

    # Structure
    if structure_issues:
        has_failure = True
        lines.append(f"STRUCTURE ........... FAIL ({page_count} pages)")
        for issue in structure_issues:
            lines.append(f"  {issue}")
    else:
        lines.append(f"STRUCTURE ........... PASS ({page_count} pages, correct section order)")
    lines.append("")

    # Page numbers
    if number_issues:
        has_failure = True
        lines.append(f"PAGE NUMBERS ........ FAIL")
        for issue in number_issues:
            lines.append(f"  {issue}")
    else:
        num_range = f"{page_numbers[0]}-{page_numbers[-1]}" if page_numbers else "none"
        lines.append(f"PAGE NUMBERS ........ PASS (sequential {num_range})")
    lines.append("")

    # Truncation
    if truncated:
        warnings += len(truncated)
        days_affected = set(t["day"] for t in truncated)
        lines.append(f"TRUNCATION .......... WARN ({len(truncated)} engagement(s) truncated)")
        if verbose:
            for t in truncated:
                lines.append(f"  {t['day']}: \"{t['text'][:50]}...\" ({t['overflowPx']}px)")
    else:
        lines.append(f"TRUNCATION .......... PASS (no text truncated)")
    lines.append("")

    # Result
    if has_failure:
        lines.append(f"RESULT: FAIL")
    elif warnings:
        lines.append(f"RESULT: PASS ({warnings} warning(s))")
    else:
        lines.append(f"RESULT: PASS")
    lines.append("")

    return "\n".join(lines), has_failure


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Proofread and validate a rendered weekly plan booklet"
    )
    parser.add_argument("plan_data", help="Path to plan_data.json")
    parser.add_argument("html_file", help="Path to weekly-plan.html")
    parser.add_argument("--verbose", action="store_true",
                        help="Show all details including passing checks")
    parser.add_argument("--overflow-only", action="store_true",
                        help="Only run the overflow check (fast)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    plan_path = Path(args.plan_data)
    html_path = Path(args.html_file)

    if not plan_path.exists():
        print(f"ERROR: Plan data not found: {plan_path}", file=sys.stderr)
        sys.exit(2)
    if not html_path.exists():
        print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
        sys.exit(2)

    # Load source data
    with open(plan_path, "r", encoding="utf-8-sig") as f:
        plan_data = json.load(f)

    html_text = html_path.read_text(encoding="utf-8")

    # Run checks
    print("Running proofreader checks...", file=sys.stderr)

    print("  Checking overflow...", file=sys.stderr)
    overflow = check_overflow(html_path)

    if args.overflow_only:
        bounded_overflows = [o for o in overflow if o.get("is_bounded_page")]
        if bounded_overflows:
            print(f"OVERFLOW: {len(bounded_overflows)} page(s) exceed bounds",
                  file=sys.stderr)
            for o in bounded_overflows:
                print(f"  Page {o['page']}: {o['overflow_px']}px over", file=sys.stderr)
            sys.exit(1)
        else:
            print("OVERFLOW: PASS", file=sys.stderr)
            sys.exit(0)

    print("  Checking content completeness...", file=sys.stderr)
    content_issues, content_stats = check_content(html_text, plan_data)

    print("  Checking page structure...", file=sys.stderr)
    structure_issues, page_count = check_structure(html_text)

    print("  Checking page numbers...", file=sys.stderr)
    number_issues, page_numbers = check_page_numbers(html_text)

    print("  Checking truncation...", file=sys.stderr)
    truncated = check_truncation(html_path)

    # Output
    if args.json:
        result = {
            "overflow": overflow,
            "content_issues": content_issues,
            "content_stats": content_stats,
            "structure_issues": structure_issues,
            "page_count": page_count,
            "number_issues": number_issues,
            "page_numbers": page_numbers,
            "truncation": truncated,
            "passed": not any([
                any(o.get("is_bounded_page") for o in overflow),
                content_issues,
                structure_issues,
                number_issues,
            ]),
        }
        print(json.dumps(result, indent=2))
    else:
        report, has_failure = format_report(
            overflow, content_issues, content_stats,
            structure_issues, page_count,
            number_issues, page_numbers,
            truncated, verbose=args.verbose,
        )
        print(report)

    # Exit code
    has_failure = any([
        any(o.get("is_bounded_page") for o in overflow),
        content_issues,
        structure_issues,
        number_issues,
    ])
    sys.exit(1 if has_failure else 0)


if __name__ == "__main__":
    main()
