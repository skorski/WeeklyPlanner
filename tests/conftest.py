"""Shared fixtures for weekly planner skill tests."""
import json
import copy
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_day(index: int, *, valid: bool = True) -> dict:
    """Build a single day entry with all required fields."""
    day_names = [
        "Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday",
    ]
    name = day_names[index % 7]
    day = {
        "name": name[:3],
        "long_name": f"{name}, February {16 + index}",
        "day_of_week": name,
        "weather": "Clear",
        "weather_detail": "Sunny with a high of 55°F",
        "weather_high": 55,
        "weather_low": 32,
        "weather_condition": "clear",
        "weather_emoji": "☀️",
        "weather_oneliner": "55° / 32° · Clear skies all day",
        "calendar": "",
        "calendar_items": [],
        "engagements": [
            {"time": "5:00 PM", "event": "Family dinner", "event_short": "Dinner"}
        ],
        "time_constraints": "",
        "dinner": f"Test Dinner {index + 1}",
        "dinner_cuisine": "Italian",
        "dinner_description": (
            "A wonderful homemade dish with rich flavors and fresh seasonal ingredients "
            "that the whole family will enjoy on this lovely evening."
        ),
        "dinner_key_ingredients": ["pasta", "tomato", "basil"],
        "dinner_source_url": "https://example.com/recipe",
        "dinner_source_name": "Test Kitchen",
        "dinner_notes": "",
        "dinner_nutrition_notes": "Good source of carbs and vitamins.",
        "album": f"Test Album {index + 1}",
        "album_artist": f"Artist {index + 1}",
        "album_title": f"Test Album {index + 1}",
        "album_year": "2024",
        "album_genre": "Indie",
        "album_mood": "Upbeat",
        "album_description": "A vibrant album with catchy melodies.",
        "album_sonic_description": "Warm guitar tones with driving percussion.",
        "album_pairing_rationale": (
            f"The upbeat energy pairs perfectly with Test Dinner {index + 1}."
        ),
        "album_spotify_url": "https://open.spotify.com/album/test",
        "activity": "",
        "activity_notes": "",
        "prep_notes": "",
        "dinner_elevation_tips": [
            {
                "type": "Sauce",
                "title": "Silky Finish",
                "instruction": "Stir in butter off heat for glossy texture.",
            },
            {
                "type": "Technique",
                "title": "Char the Edges",
                "instruction": "Broil for 2 minutes to develop caramelization.",
            },
        ],
        "dinner_question": {
            "question": "What was the best part of your day?",
            "why": "Encourages positive reflection and gratitude.",
        },
        "day_intro": (
            "A bright and cheerful day awaits the family. "
            "The kitchen will be full of warmth and wonderful aromas."
        ),
        "recipe_card": {
            "nonna_says": (
                "Heat the oil in your biggest pan. Not too hot — medium. "
                "Add the garlic, let it sing. Tomatoes go in, crush them "
                "with your spoon. Simmer low and slow. Taste it. Trust yourself."
            ),
            "engineer_table": {
                "preheat": "",
                "groups": [
                    {
                        "ingredients": [
                            {"qty": "2 tbsp", "item": "olive oil", "prep": ""},
                            {"qty": "3 cloves", "item": "garlic", "prep": "minced"},
                        ],
                        "merge_action": "heat over medium",
                    },
                    {
                        "ingredients": [
                            {"qty": "28 oz", "item": "crushed tomatoes", "prep": ""},
                            {"qty": "1 tsp", "item": "salt", "prep": ""},
                        ],
                        "merge_action": "simmer 20 min",
                    },
                ],
                "final_steps": ["toss with pasta", "finish with basil"],
            },
            "variations": [
                {
                    "name": "Spicy Arrabbiata",
                    "twist": "Add red pepper flakes for heat",
                    "source_url": "https://example.com/arrabbiata",
                },
                {
                    "name": "Creamy Vodka",
                    "twist": "Splash of vodka and cream for richness",
                    "source_url": "https://example.com/vodka-sauce",
                },
                {
                    "name": "Puttanesca",
                    "twist": "Capers, olives, and anchovies for brine",
                    "source_url": "https://example.com/puttanesca",
                },
            ],
        },
    }
    if not valid:
        # Introduce common errors for negative testing
        day["dinner_question"] = "What was the best part of your day?"
        day["dinner_elevation_tips"] = ["Stir in butter off heat"]
        day["recipe_card"] = None
    return day


def _make_principles(*, valid: bool = True) -> dict:
    """Build principles_data with proper structure."""
    word_block = "Lorem ipsum dolor sit amet " * 18  # ~90 words
    essay = f"{word_block.strip()}\n\n{word_block.strip()}"  # 2 paragraphs, ~180 words
    if valid:
        essay = ("This is a detailed exploration of the principle at hand. " * 25).strip()
        essay += "\n\n"
        essay += ("Practical application means taking these ideas seriously. " * 25).strip()
    entries = []
    for i in range(7):
        entries.append({
            "day": ["Sunday", "Monday", "Tuesday", "Wednesday",
                    "Thursday", "Friday", "Saturday"][i],
            "title": f"Principle {i + 1}",
            "thinker": "Marcus Aurelius",
            "essay": essay,
        })
    return {
        "theme": {
            "title": "Discipline Equals Freedom",
            "category": "Self-Mastery",
            "description": "Exploring how structure creates space for creativity.",
        },
        "daily_entries": entries,
    }


def _make_stoic(*, valid: bool = True) -> dict:
    """Build stoic_data with proper structure."""
    data = {
        "theme": {
            "title": "The Inner Citadel",
            "category": "Resilience",
            "description": "Building unshakable inner strength.",
        },
        "anchor_quote": {
            "text": "The impediment to action advances action.",
            "source": "Marcus Aurelius",
            "work": "Meditations",
            "reference": "V.20",
        },
        "meditations": [
            {
                "day": "Sunday",
                "title": "Morning Reflection",
                "meditation": "Begin the day by telling yourself...",
                "journaling_prompt": "What obstacle can I reframe today?",
            }
            for _ in range(7)
        ],
        "family_exercise": "Discuss one challenge each family member overcame.",
        "young_stoic": {
            "title": "The Unbreakable Shield",
            "story": "Once there was a girl who found a shield...",
        },
    }
    if not valid:
        data["theme"] = "The Inner Citadel"  # wrong: string instead of dict
        data.pop("anchor_quote")
        data["days"] = data.pop("meditations")  # wrong key name
    return data


def _make_parenting(*, valid: bool = True) -> dict:
    """Build parenting_data with proper structure."""
    data = {
        "weekly_theme": {
            "title": "Building Resilience",
            "description": "Helping kids bounce back from setbacks.",
        },
        "dinner_questions": [
            {
                "day": ["Sunday", "Monday", "Tuesday", "Wednesday",
                        "Thursday", "Friday", "Saturday"][i],
                "question": f"What made you laugh today? (Day {i+1})",
                "why": "Encourages joy and social connection.",
            }
            for i in range(7)
        ],
        "nudges": [
            {"title": "Growth Mindset", "description": "Praise effort not outcome."},
            {"title": "Empathy Practice", "description": "Ask how a friend felt."},
            {"title": "Responsibility", "description": "Let her set the table."},
        ],
        "recommendation": {
            "title": "The Whole-Brain Child",
            "author": "Daniel J. Siegel",
            "description": "Practical strategies for nurturing your child's mind.",
        },
    }
    if not valid:
        data["days"] = data.pop("dinner_questions")  # wrong key
        data["weekly_theme"] = "Building Resilience"  # string not dict
    return data


def _make_story() -> dict:
    """Build story_data."""
    return {
        "title": "The Great Dinner Disaster",
        "story": ("Once upon a time there was a girl named Chelsie. " * 15).strip(),
        "discussion_prompt": "What would you do if someone served you something weird?",
    }


@pytest.fixture
def valid_plan_data() -> dict:
    """A complete, valid plan_data.json structure."""
    return {
        "week_range": "February 16 – 22, 2026",
        "days": [_make_day(i) for i in range(7)],
        "appetizers": [{"name": "Bruschetta", "description": "Classic tomato basil"}],
        "salads": [{"name": "Caesar", "description": "Romaine with parmesan"}],
        "beverages": [{"name": "Lemonade", "description": "Fresh squeezed"}],
        "grocery_list": {"produce": ["tomatoes", "basil"]},
        "prep_ahead": ["Chop veggies on Sunday"],
        "notes": "Great week ahead!",
        "generated_at": "2026-02-15T10:00:00",
        "daily_plan_subtitle": "A Week of Italian Comfort",
        "parenting_data": _make_parenting(),
        "nutrition_summary": "Well-balanced week with good variety.",
        "nutrition_data": {
            "analysis": "Covers all major food groups.",
            "lunch_suggestions": ["Turkey wrap", "Grilled cheese"],
            "snack_suggestions": ["Apple slices", "Yogurt"],
        },
        "stoic_data": _make_stoic(),
        "principles_data": _make_principles(),
        "story_data": _make_story(),
        "highlight": "Italian Comfort Food Week",
        "child_wisdom": _make_story(),
        "newsletter_data": None,
        "lunches": [],
    }


@pytest.fixture
def invalid_plan_data(valid_plan_data) -> dict:
    """A plan_data with common field shape errors."""
    data = copy.deepcopy(valid_plan_data)
    # Break field shapes in days
    for day in data["days"]:
        day["dinner_question"] = "What was the best part of your day?"
        day["dinner_elevation_tips"] = ["Just a string tip"]
        day["recipe_card"] = None
    # Break top-level sections
    data["stoic_data"] = _make_stoic(valid=False)
    data["principles_data"]["daily_entries"] = data["principles_data"].pop("daily_entries")
    data["principles_data"].pop("theme", None)
    data["parenting_data"] = _make_parenting(valid=False)
    return data


@pytest.fixture
def plan_data_path(tmp_path, valid_plan_data) -> Path:
    """Write valid plan_data.json to a temp dir and return path."""
    p = tmp_path / "plan_data.json"
    p.write_text(json.dumps(valid_plan_data, indent=2), encoding="utf-8")
    return p
