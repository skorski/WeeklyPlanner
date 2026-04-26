#!/usr/bin/env python3
"""Compatibility entry point for the content-validator skill."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WEEKLY_PLANNER_SCRIPTS = ROOT / ".github" / "skills" / "weekly-planner" / "scripts"
sys.path.insert(0, str(WEEKLY_PLANNER_SCRIPTS))

from validate_plan import main


if __name__ == "__main__":
    main()

