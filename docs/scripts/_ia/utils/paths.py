#!/usr/bin/env python3
"""
paths.py — Centralized path constants for HB Track AI scripts.

All scripts MUST import REPO_ROOT and CANON from here
instead of computing parents[N] individually.

Location: docs/scripts/_ia/utils/paths.py
"""

from pathlib import Path

# docs/scripts/_ia/utils/paths.py → docs/scripts/_ia/utils/ → docs/scripts/_ia/ → docs/ → HB TRACK/
REPO_ROOT = Path(__file__).resolve().parents[4]
CANON = REPO_ROOT / "docs" / "_canon"
SCRIPTS_IA = REPO_ROOT / "docs" / "scripts" / "_ia"
