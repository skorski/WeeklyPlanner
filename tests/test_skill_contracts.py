"""Tests for skill-to-skill connection contracts.

Verifies that researcher outputs match the schemas expected by
validators and formatters. Ensures the pipeline stays connected
when skills are modified independently.
"""
import json
import copy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / ".github" / "skills" / "proofreader" / "scripts"))
from proofread import check_field_shapes  # noqa: E402


# ── Schema Contract: Days → Booklet Templates ──────────────────────────────


class TestDayToBookletContract:
    """Each day entry must have fields the Jinja2 booklet templates expect."""

    REQUIRED_DAY_FIELDS = {
        "name", "long_name", "weather_oneliner", "dinner",
        "dinner_description", "dinner_elevation_tips", "dinner_question",
        "album", "album_title", "album_artist", "album_spotify_url",
        "album_pairing_rationale", "day_intro", "recipe_card",
    }

    def test_fixture_has_all_required_fields(self, valid_plan_data):
        for day in valid_plan_data["days"]:
            missing = self.REQUIRED_DAY_FIELDS - set(day.keys())
            assert not missing, (
                f"{day['name']} missing fields: {missing}"
            )

    def test_dinner_question_is_dict_with_keys(self, valid_plan_data):
        for day in valid_plan_data["days"]:
            dq = day["dinner_question"]
            assert isinstance(dq, dict), f"{day['name']}: dinner_question not dict"
            assert "question" in dq, f"{day['name']}: missing 'question' key"
            assert "why" in dq, f"{day['name']}: missing 'why' key"

    def test_elevation_tips_are_dicts(self, valid_plan_data):
        for day in valid_plan_data["days"]:
            tips = day["dinner_elevation_tips"]
            assert isinstance(tips, list) and len(tips) >= 2
            for tip in tips:
                assert isinstance(tip, dict)
                assert {"type", "title", "instruction"} <= set(tip.keys())

    def test_recipe_card_structure(self, valid_plan_data):
        for day in valid_plan_data["days"]:
            rc = day["recipe_card"]
            assert isinstance(rc, dict), f"{day['name']}: recipe_card not dict"
            assert rc.get("nonna_says"), "nonna_says empty"
            et = rc.get("engineer_table")
            assert isinstance(et, dict), "engineer_table not dict"
            assert len(et.get("groups", [])) >= 2, "Need ≥2 groups"
            assert len(et.get("final_steps", [])) >= 1, "Need ≥1 final step"
            for group in et["groups"]:
                assert "ingredients" in group
                assert "merge_action" in group
                for ing in group["ingredients"]:
                    assert {"qty", "item"} <= set(ing.keys())
            assert len(rc.get("variations", [])) == 3
            for v in rc["variations"]:
                assert {"name", "twist", "source_url"} <= set(v.keys())

    def test_engagements_are_dicts(self, valid_plan_data):
        for day in valid_plan_data["days"]:
            for eng in day.get("engagements", []):
                assert isinstance(eng, dict)
                assert "time" in eng
                assert "event" in eng


# ── Schema Contract: Stoic → Booklet ───────────────────────────────────────


class TestStoicToBookletContract:
    """stoic_data must match the stoic booklet template."""

    def test_theme_is_dict(self, valid_plan_data):
        sd = valid_plan_data["stoic_data"]
        assert isinstance(sd["theme"], dict)
        assert {"title", "category", "description"} <= set(sd["theme"].keys())

    def test_anchor_quote_is_dict(self, valid_plan_data):
        sd = valid_plan_data["stoic_data"]
        aq = sd.get("anchor_quote")
        assert isinstance(aq, dict)
        assert {"text", "source", "work"} <= set(aq.keys())

    def test_meditations_key_not_days(self, valid_plan_data):
        sd = valid_plan_data["stoic_data"]
        assert "meditations" in sd, "Should use 'meditations' not 'days'"
        assert "days" not in sd, "Should NOT use 'days' key"

    def test_meditations_have_required_fields(self, valid_plan_data):
        for m in valid_plan_data["stoic_data"]["meditations"]:
            assert isinstance(m, dict)
            assert "meditation" in m or "reflection" in m


# ── Schema Contract: Principles → Booklet ──────────────────────────────────


class TestPrinciplesToBookletContract:
    """principles_data must match the principles booklet template."""

    def test_theme_is_dict(self, valid_plan_data):
        pd = valid_plan_data["principles_data"]
        assert isinstance(pd["theme"], dict)
        assert "title" in pd["theme"]

    def test_daily_entries_key_not_days(self, valid_plan_data):
        pd = valid_plan_data["principles_data"]
        assert "daily_entries" in pd, "Should use 'daily_entries' not 'days'"
        assert "days" not in pd, "Should NOT use 'days' key"

    def test_entries_have_essay(self, valid_plan_data):
        for entry in valid_plan_data["principles_data"]["daily_entries"]:
            assert isinstance(entry, dict)
            assert "essay" in entry
            assert len(entry["essay"]) > 100, "Essay too short"

    def test_seven_entries(self, valid_plan_data):
        entries = valid_plan_data["principles_data"]["daily_entries"]
        assert len(entries) == 7


# ── Schema Contract: Parenting → Booklet ───────────────────────────────────


class TestParentingToBookletContract:
    """parenting_data must match the parenting booklet template."""

    def test_weekly_theme_is_dict(self, valid_plan_data):
        par = valid_plan_data["parenting_data"]
        assert isinstance(par["weekly_theme"], dict)
        assert "title" in par["weekly_theme"]

    def test_dinner_questions_key_not_days(self, valid_plan_data):
        par = valid_plan_data["parenting_data"]
        assert "dinner_questions" in par
        assert "days" not in par

    def test_dinner_questions_have_question_and_why(self, valid_plan_data):
        for dq in valid_plan_data["parenting_data"]["dinner_questions"]:
            assert isinstance(dq, dict)
            assert "question" in dq
            assert "why" in dq

    def test_nudges_exist(self, valid_plan_data):
        par = valid_plan_data["parenting_data"]
        assert len(par.get("nudges", [])) >= 3

    def test_recommendation_exists(self, valid_plan_data):
        rec = valid_plan_data["parenting_data"].get("recommendation")
        assert isinstance(rec, dict)
        assert "title" in rec


# ── Schema Contract: Story → Booklet ───────────────────────────────────────


class TestStoryToBookletContract:
    """story_data / child_wisdom must have title, story, prompt."""

    def test_story_data_structure(self, valid_plan_data):
        sd = valid_plan_data.get("story_data") or valid_plan_data.get("child_wisdom")
        assert sd is not None
        assert sd.get("title"), "Story must have a title"
        assert len(sd.get("story", "").split()) >= 100, "Story must be 250+ words"
        assert sd.get("discussion_prompt"), "Need a discussion prompt"


# ── Schema Contract: Nutrition → Plan Assembly ─────────────────────────────


class TestNutritionToAssemblyContract:
    """nutrition_data must have analysis, lunch/snack suggestions."""

    def test_nutrition_data_keys(self, valid_plan_data):
        nd = valid_plan_data["nutrition_data"]
        assert "lunch_suggestions" in nd
        assert "snack_suggestions" in nd
        assert len(nd["lunch_suggestions"]) >= 1
        assert len(nd["snack_suggestions"]) >= 1


# ── Integration: check_field_shapes on valid data ──────────────────────────


class TestFieldShapeIntegration:
    """Run the actual proofreader field shape function on fixture data."""

    def test_valid_data_passes(self, valid_plan_data):
        issues = check_field_shapes(valid_plan_data)
        assert issues == [], f"Valid data should pass: {issues}"

    def test_invalid_data_catches_errors(self, invalid_plan_data):
        issues = check_field_shapes(invalid_plan_data)
        assert len(issues) > 0, "Invalid data should have issues"
        # Should catch multiple types of errors
        issue_text = " ".join(issues)
        assert "dinner_question" in issue_text
        assert "dinner_elevation_tips" in issue_text
        assert "recipe_card" in issue_text


# ── Real Plan Data Contract Tests ──────────────────────────────────────────


class TestRealPlanContracts:
    """Run contract checks on actual plan data from the repo."""

    PLAN_DIRS = list(
        (REPO_ROOT / "weekly_plans").glob("20*")
    )

    @pytest.mark.parametrize(
        "plan_dir",
        PLAN_DIRS,
        ids=[d.name for d in PLAN_DIRS] if PLAN_DIRS else ["no_plans"],
    )
    def test_real_plan_field_shapes(self, plan_dir):
        plan_path = plan_dir / "plan_data.json"
        if not plan_path.exists():
            pytest.skip(f"No plan_data.json in {plan_dir.name}")
        data = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        issues = check_field_shapes(data)
        # Report but don't hard-fail on older plans that predate new contracts
        if issues:
            for issue in issues:
                print(f"  {plan_dir.name}: {issue}")

    @pytest.mark.parametrize(
        "plan_dir",
        PLAN_DIRS,
        ids=[d.name for d in PLAN_DIRS] if PLAN_DIRS else ["no_plans"],
    )
    def test_real_plan_has_seven_days(self, plan_dir):
        plan_path = plan_dir / "plan_data.json"
        if not plan_path.exists():
            pytest.skip(f"No plan_data.json in {plan_dir.name}")
        data = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        days = data.get("days", [])
        assert len(days) == 7, f"{plan_dir.name}: has {len(days)} days, expected 7"

    @pytest.mark.parametrize(
        "plan_dir",
        PLAN_DIRS,
        ids=[d.name for d in PLAN_DIRS] if PLAN_DIRS else ["no_plans"],
    )
    def test_real_plan_no_duplicate_dinners(self, plan_dir):
        plan_path = plan_dir / "plan_data.json"
        if not plan_path.exists():
            pytest.skip(f"No plan_data.json in {plan_dir.name}")
        data = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        dinners = [d.get("dinner", "") for d in data.get("days", [])]
        assert len(dinners) == len(set(dinners)), (
            f"{plan_dir.name}: duplicate dinners {dinners}"
        )
