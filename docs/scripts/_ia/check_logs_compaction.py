#!/usr/bin/env python3
# scripts/_ia/check_logs_compaction.py
"""
Checks that CHANGELOG.md and EXECUTION_LOG.md are "index-only" (no narrative blobs).

Rules (regex-based, pragmatic):
- No markdown bullet blocks longer than MAX_BULLET_LINES under [Unreleased] (changelog)
- No table rows where a cell contains '**Task**:' or other narrative markers
- Disallow multi-sentence paragraphs in log files (heuristic)
- Ensure both files contain a Retention/Detail policy block (recommended)

Exit codes:
  0 = OK
  2 = Violations found
  3 = File missing / read error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


# Heuristics tuned for your current patterns:
NARRATIVE_MARKERS = [
    r"\*\*Task\*\*:",
    r"\*\*Action\*\*:",
    r"\*\*Results\*\*:",
    r"\*\*Impact\*\*:",
    r"\*\*Artifacts\*\*:",
    r"\bOutcome\b:",
    r"\bObservação\b:",
]

RETENTION_MARKERS = [
    r"Retention/Detail Policy",
    r"Retention Policy",
]

def _find_repo_root(start: Path) -> Path:
    # Prefer a deterministic repo root anchor over hardcoded absolute paths.
    for p in [start] + list(start.parents):
        if (p / ".git").exists():
            return p
    # Fallback: expected layout is <repo>/docs/scripts/_ia/<this_file>
    return start.parents[4] if len(start.parents) >= 5 else start.parent


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
ARTIFACTS_DIR = REPO_ROOT / "docs" / "execution_tasks" / "artifacts"
TASK_ID_PATTERN = re.compile(r"\[([A-Z0-9-]+)\]")
# Allow short bullets. Anything beyond this is likely narrative.
MAX_BULLET_LINES = 8

# Detect "paragraph blocks" (two or more sentences) as narrative
MULTI_SENTENCE = re.compile(r"[.!?].+[.!?]")


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _has_retention_block(text: str) -> bool:
    return any(re.search(m, text, flags=re.IGNORECASE) for m in RETENTION_MARKERS)


def _find_narrative_markers(text: str) -> List[str]:
    hits = []
    for m in NARRATIVE_MARKERS:
        if re.search(m, text, flags=re.IGNORECASE):
            hits.append(m)
    return hits


def _verify_artifacts(text: str) -> List[str]:
    violations: List[str] = []
    tasks = TASK_ID_PATTERN.findall(text)
    for task_id in tasks:
        # Avoid common patterns that are not tasks
        if task_id in ["Unreleased", "Archive", "HB-LOGS-001"]: # Exclude known non-task IDs if any
            continue
        # Only check if it looks like a real task ID (e.g., ARCH-LOGS-001)
        if not re.match(r"^[A-Z0-9]+-[A-Z0-9-]+$", task_id):
            continue
            
        event_path = ARTIFACTS_DIR / task_id / "event.json"
        if not event_path.exists():
            violations.append(f"Orphaned Task Index: Task {task_id} has no artifact at docs/execution_tasks/artifacts/{task_id}/event.json")
    return list(set(violations)) # Deduplicate


def _check_changelog(text: str) -> List[str]:
    violations: List[str] = []

    # Check retention policy presence
    if not _has_retention_block(text):
        violations.append("CHANGELOG: missing Retention/Detail Policy block")

    # Heuristic: detect very long bullet blocks under Unreleased
    # Find Unreleased section chunk
    m = re.search(r"^##\s+\[Unreleased\]\s*$", text, flags=re.MULTILINE)
    if m:
        start = m.end()
        # up to next H2
        m2 = re.search(r"^##\s+\[", text[start:], flags=re.MULTILINE)
        end = start + (m2.start() if m2 else len(text[start:]))
        unreleased = text[start:end]
        bullet_lines = [ln for ln in unreleased.splitlines() if ln.strip().startswith(("-", "*"))]
        if len(bullet_lines) > MAX_BULLET_LINES:
            violations.append(f"CHANGELOG: Unreleased contains too many bullet lines ({len(bullet_lines)} > {MAX_BULLET_LINES}). Likely narrative.")
    # Narrative markers not allowed
    markers = _find_narrative_markers(text)
    if markers:
        violations.append(f"CHANGELOG: contains narrative markers: {markers}")

    # Multi-sentence paragraphs forbidden (heuristic)
    # Consider only lines that are not table rows and not list items
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("|") or s.startswith("-") or s.startswith("*") or s.startswith(">") or s.startswith("#") or s.startswith("<!--"):
            continue
        if MULTI_SENTENCE.search(s):
            violations.append("CHANGELOG: contains multi-sentence paragraph line (likely narrative)")
            break

    violations.extend(_verify_artifacts(text))

    return violations


def _check_exec_log(text: str) -> List[str]:
    violations: List[str] = []

    if not _has_retention_block(text):
        violations.append("EXECUTION_LOG: missing Retention/Detail Policy block")

    markers = _find_narrative_markers(text)
    if markers:
        violations.append(f"EXECUTION_LOG: contains narrative markers: {markers}")

    # Table rows should be short; we disallow bold blocks in table cells
    if re.search(r"^\|.*\*\*.*\*\*.*\|", text, flags=re.MULTILINE):
        violations.append("EXECUTION_LOG: contains bold/narrative content inside table rows (expected index-only table).")

    # Multi-sentence paragraphs forbidden
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("|") or s.startswith("-") or s.startswith("*") or s.startswith(">") or s.startswith("#") or s.startswith("<!--"):
            continue
        if MULTI_SENTENCE.search(s):
            violations.append("EXECUTION_LOG: contains multi-sentence paragraph line (likely narrative)")
            break

    violations.extend(_verify_artifacts(text))

    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changelog", required=True, help="Path to CHANGELOG.md")
    ap.add_argument("--exec-log", required=True, help="Path to EXECUTION_LOG.md")
    args = ap.parse_args()

    changelog = Path(args.changelog)
    exec_log = Path(args.exec_log)

    if not changelog.exists():
        print(f"ERROR: changelog not found: {changelog}", file=sys.stderr)
        return 3
    if not exec_log.exists():
        print(f"ERROR: execution log not found: {exec_log}", file=sys.stderr)
        return 3

    cl_text = _read_text(changelog)
    el_text = _read_text(exec_log)

    violations: List[Tuple[str, str]] = []
    for v in _check_changelog(cl_text):
        violations.append((str(changelog), v))
    for v in _check_exec_log(el_text):
        violations.append((str(exec_log), v))

    if violations:
        for f, msg in violations:
            print(f"{f}: {msg}", file=sys.stderr)
        print("[FAIL] Logs compaction check failed.", file=sys.stderr)
        return 2

    print("[OK] Logs compaction check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
