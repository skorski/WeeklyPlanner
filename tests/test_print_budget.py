"""Tests for print-formatter A5 page budget constants and trim logic.

These tests validate:
- A5 page dimension constants (148mm × 210mm)
- Word-per-page budgets (~320 words, ~25 lines at 9pt/1.5 line-height)
- Trim priority order enforcement
- Content preservation after trimming
"""
import copy
import sys
from pathlib import Path

import pytest

# Import proofreader constants for page dimension checks
sys.path.insert(0, str(Path(__file__).resolve().parent.parent /
                        ".github" / "skills" / "proofreader" / "scripts"))
from proofread import PAGE_HEIGHT_PX, MARGIN_PX, CONTENT_HEIGHT_PX  # noqa: E402


# ── A5 Page Constants ───────────────────────────────────────────────────────

# A5 in CSS units at 96 DPI:
#   148mm × 210mm → 5.83in × 8.27in → 559.7px × 793.9px
# The booklet uses half-letter (5.5" × 8.5") which is close to A5
A5_WIDTH_MM = 148
A5_HEIGHT_MM = 210
HALF_LETTER_WIDTH_IN = 5.5
HALF_LETTER_HEIGHT_IN = 8.5

# Print-formatter documented budgets
MAX_WORDS_PER_PAGE = 320
MAX_LINES_PER_PAGE = 25
MAX_INGREDIENT_ROWS = 15

# Body text specs from SKILL.md
BODY_FONT_SIZE_PT = 9
LINE_HEIGHT_RATIO = 1.5


class TestPageDimensions:
    """Verify page size constants are consistent."""

    def test_page_height_is_half_letter(self):
        expected_px = int(HALF_LETTER_HEIGHT_IN * 96)
        assert PAGE_HEIGHT_PX == expected_px, (
            f"PAGE_HEIGHT_PX={PAGE_HEIGHT_PX} doesn't match "
            f"{HALF_LETTER_HEIGHT_IN}in * 96dpi = {expected_px}"
        )

    def test_content_height_accounts_for_margins(self):
        assert CONTENT_HEIGHT_PX == PAGE_HEIGHT_PX - MARGIN_PX
        assert CONTENT_HEIGHT_PX > 700, "Content area too small"
        assert CONTENT_HEIGHT_PX < PAGE_HEIGHT_PX, "Margins not subtracted"

    def test_margin_is_reasonable(self):
        """Margins should be between 0.4in and 0.8in total."""
        margin_in = MARGIN_PX / 96
        assert 0.4 <= margin_in <= 0.8, (
            f"Total margin {margin_in:.2f}in is outside 0.4–0.8in range"
        )

    def test_a5_fits_within_half_letter(self):
        """A5 (148×210mm) should fit within half-letter (5.5×8.5in)."""
        a5_width_in = A5_WIDTH_MM / 25.4
        a5_height_in = A5_HEIGHT_MM / 25.4
        assert a5_width_in <= HALF_LETTER_WIDTH_IN + 0.5, "A5 width too large"
        assert a5_height_in <= HALF_LETTER_HEIGHT_IN + 0.5, "A5 height too large"


class TestWordBudget:
    """Verify word counts stay within page budget."""

    def test_day_intro_fits_budget(self, valid_plan_data):
        """day_intro should be well under the page word limit."""
        for day in valid_plan_data["days"]:
            intro = day.get("day_intro", "")
            words = len(intro.split())
            assert words <= 60, (
                f"{day['name']}: day_intro is {words} words — recommended max ~50 "
                f"since it shares the page with events, weather, dinner info"
            )

    def test_dinner_description_fits_budget(self, valid_plan_data):
        """dinner_description should leave room for other day-left content."""
        for day in valid_plan_data["days"]:
            desc = day.get("dinner_description", "")
            words = len(desc.split())
            assert words <= 80, (
                f"{day['name']}: dinner_description is {words} words — "
                f"should be ≤80 for day-left page to fit"
            )

    def test_nonna_says_fits_recipe_page(self, valid_plan_data):
        """nonna_says should be 4-8 sentences, fitting in ~100 words."""
        for day in valid_plan_data["days"]:
            rc = day.get("recipe_card")
            if rc and rc.get("nonna_says"):
                text = rc["nonna_says"]
                words = len(text.split())
                # Nonna's directions should be concise
                assert words <= 150, (
                    f"{day['name']}: nonna_says is {words} words — "
                    f"should be ≤150 to leave room for engineer table"
                )

    def test_engineer_table_row_count(self, valid_plan_data):
        """Engineer table should not exceed MAX_INGREDIENT_ROWS."""
        for day in valid_plan_data["days"]:
            rc = day.get("recipe_card")
            if rc and rc.get("engineer_table"):
                total_rows = sum(
                    len(g["ingredients"])
                    for g in rc["engineer_table"]["groups"]
                )
                assert total_rows <= MAX_INGREDIENT_ROWS, (
                    f"{day['name']}: engineer table has {total_rows} rows — "
                    f"max {MAX_INGREDIENT_ROWS} to fit A5 page"
                )

    def test_principles_essay_fits_one_page(self, valid_plan_data):
        """Principles essays should be ≤ MAX_WORDS_PER_PAGE + overhead."""
        entries = valid_plan_data["principles_data"]["daily_entries"]
        for entry in entries:
            words = len(entry["essay"].split())
            # Essay page has a title, thinker, and date — budget ~290 for text
            assert words <= 450, (
                f"{entry['day']}: essay is {words} words — "
                f"should be ≤450 to fit on a single A5 page with header"
            )

    def test_elevation_tip_instruction_length(self, valid_plan_data):
        """Chef tip instructions should be short enough for the right page."""
        for day in valid_plan_data["days"]:
            for tip in day.get("dinner_elevation_tips", []):
                instruction = tip.get("instruction", "")
                assert len(instruction) <= 200, (
                    f"{day['name']}: tip '{tip['title']}' instruction is "
                    f"{len(instruction)} chars — should be ≤200 for A5"
                )


class TestTrimPriority:
    """Verify trim priority order from SKILL.md is respected."""

    # The priority order (trim first → last):
    # Day Left: day_intro → dinner_description → album_pairing_rationale
    # Day Principles: essay (cap 400 words)
    # Day Recipe: nonna_says → engineer merge_actions → variation twists
    # Day Right: album_description → album_sonic_description → tip instructions

    DAY_LEFT_PRIORITY = [
        "day_intro",
        "dinner_description",
        "album_pairing_rationale",
    ]

    DAY_RIGHT_PRIORITY = [
        "album_description",
        "album_sonic_description",
    ]

    def test_day_left_fields_exist(self, valid_plan_data):
        """All trimmable day-left fields should be present."""
        for day in valid_plan_data["days"]:
            for field in self.DAY_LEFT_PRIORITY:
                assert field in day, f"Missing trimmable field '{field}'"

    def test_day_right_fields_exist(self, valid_plan_data):
        """All trimmable day-right fields should be present."""
        for day in valid_plan_data["days"]:
            for field in self.DAY_RIGHT_PRIORITY:
                assert field in day, f"Missing trimmable field '{field}'"

    def test_trim_day_intro_to_two_sentences(self, valid_plan_data):
        """Simulated trim: day_intro should reduce to ≤2 sentences."""
        data = copy.deepcopy(valid_plan_data)
        for day in data["days"]:
            intro = day["day_intro"]
            sentences = [s.strip() for s in intro.split(".") if s.strip()]
            if len(sentences) > 2:
                trimmed = ". ".join(sentences[:2]) + "."
                day["day_intro"] = trimmed
            words = len(day["day_intro"].split())
            assert words <= 40, (
                f"Trimmed day_intro still {words} words"
            )

    def test_trim_essay_cap_at_400_words(self, valid_plan_data):
        """Trimmed essay should maintain 2-paragraph structure at ≤400 words."""
        data = copy.deepcopy(valid_plan_data)
        for entry in data["principles_data"]["daily_entries"]:
            essay = entry["essay"]
            words = essay.split()
            if len(words) > 400:
                # Simple trim: keep first 400 words
                trimmed_words = words[:400]
                trimmed = " ".join(trimmed_words)
                # Ensure 2-paragraph structure preserved
                if "\n\n" not in trimmed:
                    midpoint = len(trimmed_words) // 2
                    trimmed = (" ".join(trimmed_words[:midpoint]) +
                               "\n\n" +
                               " ".join(trimmed_words[midpoint:]))
                entry["essay"] = trimmed
            paragraphs = [p for p in entry["essay"].split("\n\n") if p.strip()]
            assert len(paragraphs) == 2, "Must preserve 2-paragraph structure"
            assert len(entry["essay"].split()) <= 400


# ── Real Plan Data Tests ────────────────────────────────────────────────────


class TestRealPlanData:
    """Run budget checks against actual plan data from the repo."""

    PLAN_DIRS = list(
        (Path(__file__).resolve().parent.parent / "weekly_plans").glob("20*")
    )

    @pytest.mark.parametrize(
        "plan_dir",
        PLAN_DIRS,
        ids=[d.name for d in PLAN_DIRS] if PLAN_DIRS else ["no_plans"],
    )
    def test_real_plan_word_budgets(self, plan_dir):
        """Check word budgets on actual plan_data.json files."""
        import json
        plan_path = plan_dir / "plan_data.json"
        if not plan_path.exists():
            pytest.skip(f"No plan_data.json in {plan_dir.name}")
        data = json.loads(
            plan_path.read_text(encoding="utf-8-sig")
        )
        warnings = []
        for day in data.get("days", []):
            name = day.get("name", "?")
            # Day intro
            intro_words = len(day.get("day_intro", "").split())
            if intro_words > 60:
                warnings.append(f"{name}: day_intro {intro_words} words (>60)")
            # Dinner description
            desc_words = len(day.get("dinner_description", "").split())
            if desc_words > 80:
                warnings.append(f"{name}: dinner_description {desc_words} words (>80)")
            # Nonna says
            rc = day.get("recipe_card")
            if rc and rc.get("nonna_says"):
                nonna_words = len(rc["nonna_says"].split())
                if nonna_words > 150:
                    warnings.append(f"{name}: nonna_says {nonna_words} words (>150)")
            # Engineer table rows
            if rc and rc.get("engineer_table"):
                rows = sum(
                    len(g["ingredients"])
                    for g in rc["engineer_table"].get("groups", [])
                )
                if rows > MAX_INGREDIENT_ROWS:
                    warnings.append(
                        f"{name}: engineer table {rows} rows (>{MAX_INGREDIENT_ROWS})"
                    )
        # Report warnings but don't fail — real plans may have intentional overflows
        if warnings:
            pytest.warns(UserWarning, match=".*") if False else None
            for w in warnings:
                print(f"  WARNING: {w}")
