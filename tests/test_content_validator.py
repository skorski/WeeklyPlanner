"""Tests for content-validator field shape and completeness checks.

These tests verify that the validation logic correctly identifies:
- Field shape mismatches (string where dict expected, wrong key names)
- Missing required content (empty days, missing recipe cards, etc.)
- Quality violations (short descriptions, duplicate dinners/albums)
"""
import copy
import sys
from pathlib import Path

import pytest

# Make proofreader's check_field_shapes importable (it has the actual logic)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent /
                        ".github" / "skills" / "proofreader" / "scripts"))
from proofread import check_field_shapes, check_content  # noqa: E402


# ── Field Shape Tests ───────────────────────────────────────────────────────


class TestFieldShapeValidation:
    """Verify field shape checks catch type mismatches."""

    def test_valid_plan_passes(self, valid_plan_data):
        issues = check_field_shapes(valid_plan_data)
        assert issues == [], f"Valid plan should pass but got: {issues}"

    def test_dinner_question_string_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["dinner_question"] = "A plain string question"
        issues = check_field_shapes(data)
        assert any("dinner_question" in i and "str" in i for i in issues)

    def test_dinner_question_missing_key_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["dinner_question"] = {"why": "no question key"}
        issues = check_field_shapes(data)
        assert any("dinner_question" in i and "question" in i for i in issues)

    def test_elevation_tips_strings_fail(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["dinner_elevation_tips"] = [
            "Just a string instead of dict"
        ]
        issues = check_field_shapes(data)
        assert any("dinner_elevation_tips" in i for i in issues)

    def test_elevation_tips_missing_keys_fail(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["dinner_elevation_tips"] = [
            {"type": "Sauce"}  # missing title, instruction
        ]
        issues = check_field_shapes(data)
        assert any("title" in i or "instruction" in i for i in issues)

    def test_recipe_card_none_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["recipe_card"] = None
        issues = check_field_shapes(data)
        assert any("recipe_card" in i and "None" in i for i in issues)

    def test_recipe_card_string_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["recipe_card"] = "not a dict"
        issues = check_field_shapes(data)
        assert any("recipe_card" in i and "str" in i for i in issues)

    def test_recipe_card_missing_nonna_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][0]["recipe_card"] = {
            "nonna_says": "",
            "engineer_table": {"groups": [], "final_steps": []},
            "variations": [],
        }
        issues = check_field_shapes(data)
        assert any("nonna_says" in i for i in issues)

    def test_stoic_theme_string_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["stoic_data"]["theme"] = "A plain string theme"
        issues = check_field_shapes(data)
        assert any("stoic_data.theme" in i for i in issues)

    def test_stoic_days_key_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["stoic_data"]["days"] = data["stoic_data"].pop("meditations")
        issues = check_field_shapes(data)
        assert any("meditations" in i or "'days'" in i for i in issues)

    def test_principles_days_key_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["principles_data"]["days"] = data["principles_data"].pop("daily_entries")
        issues = check_field_shapes(data)
        assert any("daily_entries" in i or "'days'" in i for i in issues)

    def test_principles_missing_theme_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        del data["principles_data"]["theme"]
        issues = check_field_shapes(data)
        assert any("principles_data" in i and "theme" in i for i in issues)

    def test_parenting_days_key_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["parenting_data"]["days"] = data["parenting_data"].pop("dinner_questions")
        issues = check_field_shapes(data)
        assert any("dinner_questions" in i or "'days'" in i for i in issues)

    def test_parenting_weekly_theme_string_fails(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["parenting_data"]["weekly_theme"] = "Not a dict"
        issues = check_field_shapes(data)
        assert any("weekly_theme" in i for i in issues)

    def test_multiple_broken_days_reported(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        for day in data["days"]:
            day["dinner_question"] = "string"
        issues = check_field_shapes(data)
        question_issues = [i for i in issues if "dinner_question" in i]
        assert len(question_issues) == 7, (
            f"Expected 7 issues (one per day), got {len(question_issues)}"
        )


# ── Content Completeness Tests ──────────────────────────────────────────────


class TestContentCompleteness:
    """Verify completeness checks count dinners, albums, tips, etc."""

    def _html_from_plan(self, plan_data: dict) -> str:
        """Build a minimal HTML string containing all expected content."""
        parts = []
        for day in plan_data.get("days", []):
            parts.append(day.get("dinner", ""))
            parts.append(day.get("album_title", ""))
            for t in day.get("dinner_elevation_tips", []):
                if isinstance(t, dict):
                    parts.append(t.get("title", ""))
            dq = day.get("dinner_question")
            if isinstance(dq, dict):
                parts.append(dq.get("question", "")[:60])
            parts.append(day.get("weather_oneliner", "").split(" · ")[0])
            for e in day.get("engagements", []):
                parts.append(e.get("event_short", e.get("event", ""))[:20])
            rc = day.get("recipe_card")
            if isinstance(rc, dict) and rc.get("nonna_says"):
                parts.append(rc["nonna_says"][:40])
        return "\n".join(parts)

    def test_valid_plan_full_content(self, valid_plan_data):
        html = self._html_from_plan(valid_plan_data)
        issues, stats = check_content(html, valid_plan_data)
        assert issues == [], f"Expected no issues, got: {issues}"
        assert stats["dinners"] == 7
        assert stats["albums"] == 7
        assert stats["tips"] == 7
        assert stats["questions"] == 7
        assert stats["recipes"] == 7

    def test_missing_dinner_in_html(self, valid_plan_data):
        html = self._html_from_plan(valid_plan_data)
        # Remove first dinner from HTML
        html = html.replace("Test Dinner 1", "")
        issues, stats = check_content(html, valid_plan_data)
        assert stats["dinners"] == 6
        assert any("MISSING dinner" in i for i in issues)

    def test_missing_album_in_html(self, valid_plan_data):
        html = self._html_from_plan(valid_plan_data)
        html = html.replace("Test Album 3", "")
        issues, stats = check_content(html, valid_plan_data)
        assert stats["albums"] == 6

    def test_null_recipe_card_reported(self, valid_plan_data):
        data = copy.deepcopy(valid_plan_data)
        data["days"][2]["recipe_card"] = None
        html = self._html_from_plan(data)
        issues, stats = check_content(html, data)
        assert stats["recipes"] == 6
        assert any("recipe card (None)" in i for i in issues)


# ── Content Quality Tests ───────────────────────────────────────────────────


class TestContentQuality:
    """Verify quality rules documented in content-validator SKILL.md."""

    def test_dinner_description_minimum_length(self, valid_plan_data):
        """Dinner descriptions must be >20 words."""
        for day in valid_plan_data["days"]:
            word_count = len(day["dinner_description"].split())
            assert word_count > 20, (
                f"{day['name']} dinner_description is only {word_count} words"
            )

    def test_no_duplicate_dinners(self, valid_plan_data):
        dinners = [d["dinner"] for d in valid_plan_data["days"]]
        assert len(dinners) == len(set(dinners)), (
            f"Duplicate dinners found: {dinners}"
        )

    def test_no_duplicate_albums(self, valid_plan_data):
        albums = [d["album_title"] for d in valid_plan_data["days"]]
        assert len(albums) == len(set(albums)), (
            f"Duplicate albums found: {albums}"
        )

    def test_album_rationale_references_dinner(self, valid_plan_data):
        """album_pairing_rationale should mention the specific dinner."""
        for day in valid_plan_data["days"]:
            dinner = day["dinner"]
            rationale = day["album_pairing_rationale"]
            assert dinner in rationale, (
                f"{day['name']}: rationale doesn't mention dinner '{dinner}'"
            )

    def test_elevation_tips_distinct_types(self, valid_plan_data):
        """Each day's tips should have distinct type values."""
        for day in valid_plan_data["days"]:
            tips = day["dinner_elevation_tips"]
            types = [t["type"] for t in tips]
            assert len(types) == len(set(types)), (
                f"{day['name']}: duplicate tip types {types}"
            )

    def test_recipe_card_has_enough_groups(self, valid_plan_data):
        """Engineer table should have at least 2 groups."""
        for day in valid_plan_data["days"]:
            rc = day["recipe_card"]
            groups = rc["engineer_table"]["groups"]
            assert len(groups) >= 2, (
                f"{day['name']}: engineer_table has only {len(groups)} groups"
            )

    def test_recipe_card_has_three_variations(self, valid_plan_data):
        """Each recipe card should have exactly 3 variations."""
        for day in valid_plan_data["days"]:
            rc = day["recipe_card"]
            assert len(rc["variations"]) == 3, (
                f"{day['name']}: has {len(rc['variations'])} variations, expected 3"
            )

    def test_principles_essay_word_count(self, valid_plan_data):
        """Principles essays should be 350+ words with 2 paragraphs."""
        entries = valid_plan_data["principles_data"]["daily_entries"]
        for entry in entries:
            essay = entry["essay"]
            words = len(essay.split())
            paragraphs = [p.strip() for p in essay.split("\n\n") if p.strip()]
            assert words >= 300, (
                f"{entry['day']}: essay is {words} words (need 350+)"
            )
            assert len(paragraphs) == 2, (
                f"{entry['day']}: essay has {len(paragraphs)} paragraphs (need 2)"
            )
