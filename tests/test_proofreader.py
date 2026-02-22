"""Tests for proofreader post-render validation functions.

Tests check_content, check_structure, check_page_numbers, and format_report
without requiring Playwright (those functions parse HTML strings directly).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent /
                        ".github" / "skills" / "proofreader" / "scripts"))
from proofread import (  # noqa: E402
    check_content,
    check_structure,
    check_page_numbers,
    format_report,
)


def _make_booklet_html(days_data, *, include_cover=True, include_back=True,
                       include_glance=True, include_divider=True,
                       four_page_layout=True) -> str:
    """Build a minimal booklet HTML string for testing structure checks."""
    pages = []
    if include_cover:
        pages.append('<div class="page page-cover"><h1>Weekly Plan</h1>'
                     '<div class="page-folio"></div></div>')
    if include_glance:
        pages.append('<div class="page page-glance">'
                     '<div class="page-folio">2</div></div>')
    if include_divider:
        pages.append('<div class="page page-divider">'
                     '<div class="divider-title">Daily Plan</div>'
                     '<div class="page-folio">3</div></div>')

    folio = 4
    for i, day in enumerate(days_data):
        dinner = day.get("dinner", f"Dinner {i+1}")
        album = day.get("album_title", f"Album {i+1}")
        tips = day.get("dinner_elevation_tips", [])
        tip_html = "".join(
            f'<span>{t["title"]}</span>' for t in tips if isinstance(t, dict)
        )
        dq = day.get("dinner_question", {})
        q_text = dq.get("question", "")[:60] if isinstance(dq, dict) else ""
        weather = day.get("weather_oneliner", "").split(" · ")[0]
        eng_html = "".join(
            f'<span>{e.get("event_short", e.get("event", ""))[:20]}</span>'
            for e in day.get("engagements", [])
        )
        rc = day.get("recipe_card")
        nonna_snip = ""
        if isinstance(rc, dict) and rc.get("nonna_says"):
            nonna_snip = rc["nonna_says"][:40]

        # Day left
        pages.append(
            f'<div class="page page-day-left">'
            f'{dinner} {q_text} {weather} {eng_html}'
            f'<div class="page-folio">{folio}</div></div>'
        )
        folio += 1

        if four_page_layout:
            # Principles page
            pages.append(
                f'<div class="page page-day-principles">'
                f'<div class="page-folio">{folio}</div></div>'
            )
            folio += 1
            # Recipe page
            pages.append(
                f'<div class="page page-day-recipe">'
                f'{nonna_snip}'
                f'<div class="page-folio">{folio}</div></div>'
            )
            folio += 1

        # Day right
        pages.append(
            f'<div class="page page-day-right">'
            f'{album} {tip_html}'
            f'<div class="page-folio">{folio}</div></div>'
        )
        folio += 1

    if include_back:
        pages.append('<div class="page page-back">'
                     '<div class="page-folio"></div></div>')

    return "\n".join(pages)


# ── Structure Tests ─────────────────────────────────────────────────────────


class TestCheckStructure:
    """Test booklet page structure validation."""

    def test_valid_structure(self, valid_plan_data):
        html = _make_booklet_html(valid_plan_data["days"])
        issues, total = check_structure(html)
        assert issues == [], f"Valid structure has issues: {issues}"
        # Cover + glance + divider + 7 days × 4 pages + back = 32
        assert total == 32

    def test_missing_cover(self, valid_plan_data):
        html = _make_booklet_html(
            valid_plan_data["days"], include_cover=False
        )
        issues, _ = check_structure(html)
        assert any("cover" in i.lower() or "glance" in i.lower() for i in issues)

    def test_missing_back_cover(self, valid_plan_data):
        html = _make_booklet_html(
            valid_plan_data["days"], include_back=False
        )
        issues, _ = check_structure(html)
        assert any("back cover" in i.lower() for i in issues)

    def test_empty_html(self):
        issues, total = check_structure("")
        assert total == 0
        assert len(issues) == 1  # "No .page elements found"

    def test_two_page_layout(self, valid_plan_data):
        html = _make_booklet_html(
            valid_plan_data["days"], four_page_layout=False
        )
        issues, total = check_structure(html)
        assert issues == [], f"2-page layout issues: {issues}"
        # Cover + glance + divider + 7 days × 2 pages + back = 18
        assert total == 18


# ── Page Numbers Tests ──────────────────────────────────────────────────────


class TestCheckPageNumbers:
    """Test page number sequence validation."""

    def test_sequential_numbers(self, valid_plan_data):
        html = _make_booklet_html(valid_plan_data["days"])
        issues, numbers = check_page_numbers(html)
        assert issues == [], f"Sequential numbers have issues: {issues}"
        assert numbers[0] == 2  # Cover has no number, glance is 2
        # Check strictly increasing
        for i in range(1, len(numbers)):
            assert numbers[i] == numbers[i - 1] + 1

    def test_gap_detected(self):
        html = (
            '<div class="page page-cover"><div class="page-folio"></div></div>'
            '<div class="page page-glance"><div class="page-folio">2</div></div>'
            '<div class="page page-day-left"><div class="page-folio">3</div></div>'
            '<div class="page page-day-right"><div class="page-folio">5</div></div>'
        )
        issues, numbers = check_page_numbers(html)
        assert any("gap" in i.lower() for i in issues)
        assert numbers == [2, 3, 5]


# ── Content Completeness Tests ──────────────────────────────────────────────


class TestCheckContent:
    """Test content-in-HTML verification."""

    def test_all_content_present(self, valid_plan_data):
        html = _make_booklet_html(valid_plan_data["days"])
        issues, stats = check_content(html, valid_plan_data)
        assert issues == [], f"Content issues: {issues}"
        assert stats["dinners"] == 7
        assert stats["albums"] == 7

    def test_missing_dinner_detected(self, valid_plan_data):
        html = _make_booklet_html(valid_plan_data["days"])
        # Corrupt HTML by removing a dinner
        html = html.replace("Test Dinner 4", "REMOVED")
        issues, stats = check_content(html, valid_plan_data)
        assert stats["dinners"] == 6
        assert any("Test Dinner 4" in i for i in issues)

    def test_missing_recipe_detected(self, valid_plan_data):
        import copy
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["recipe_card"] = None
        html = _make_booklet_html(data["days"])
        issues, stats = check_content(html, data)
        assert stats["recipes"] == 6


# ── Report Formatting Tests ─────────────────────────────────────────────────


class TestFormatReport:
    """Test the human-readable report formatter."""

    def test_pass_report(self):
        report, has_failure = format_report(
            overflow=[],
            content_issues=[],
            content_stats={
                "dinners": 7, "albums": 7, "tips": 7,
                "questions": 7, "weather": 7, "engagements": 7, "recipes": 7,
            },
            structure_issues=[],
            page_count=42,
            number_issues=[],
            page_numbers=list(range(2, 32)),
            truncated=[],
        )
        assert "PASS" in report
        assert not has_failure

    def test_fail_report_on_content(self):
        report, has_failure = format_report(
            overflow=[],
            content_issues=["MISSING dinner 'Pasta' for Monday"],
            content_stats={
                "dinners": 6, "albums": 7, "tips": 7,
                "questions": 7, "weather": 7, "engagements": 7, "recipes": 7,
            },
            structure_issues=[],
            page_count=42,
            number_issues=[],
            page_numbers=list(range(2, 32)),
            truncated=[],
        )
        assert "FAIL" in report
        assert has_failure

    def test_fail_report_on_overflow(self):
        report, has_failure = format_report(
            overflow=[{
                "page": 5,
                "label": "Monday",
                "classes": "page page-day-left",
                "overflow_px": 30,
                "is_day_page": True,
                "is_bounded_page": True,
            }],
            content_issues=[],
            content_stats={
                "dinners": 7, "albums": 7, "tips": 7,
                "questions": 7, "weather": 7, "engagements": 7, "recipes": 7,
            },
            structure_issues=[],
            page_count=42,
            number_issues=[],
            page_numbers=list(range(2, 32)),
            truncated=[],
        )
        assert "OVERFLOW" in report
        assert "FAIL" in report
        assert has_failure

    def test_no_field_shapes_in_report(self):
        """Field shapes check was moved to content-validator — should not appear."""
        report, _ = format_report(
            overflow=[],
            content_issues=[],
            content_stats={
                "dinners": 7, "albums": 7, "tips": 7,
                "questions": 7, "weather": 7, "engagements": 7, "recipes": 7,
            },
            structure_issues=[],
            page_count=42,
            number_issues=[],
            page_numbers=list(range(2, 32)),
            truncated=[],
        )
        assert "FIELD SHAPES" not in report
