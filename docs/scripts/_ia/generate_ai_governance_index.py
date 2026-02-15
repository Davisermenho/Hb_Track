#!/usr/bin/env python3
# scripts/_ia/generate_ai_governance_index.py
"""
Deterministic generator for docs/_canon/AI_GOVERNANCE_INDEX.md.

- Scans fixed roots
- Groups by LEVEL (hardcoded mapping)
- Produces stable, reproducible markdown
- --write writes the file
- --check fails if current file differs from generated

Exit codes:
  0 = OK
  2 = Differences found (in --check)
  3 = Error (bad paths, missing required files, etc.)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


REPO_ROOT_DEFAULT = "."


# --- Canonical paths (relative to repo root) ---
CANON_REQUIRED = [
    "docs/_canon/AI_KERNEL.md",
    # You may add more required ones if your constitution mandates it
]

OUTPUT_INDEX = "docs/_canon/AI_GOVERNANCE_INDEX.md"

SCAN_ROOTS = [
    "docs/_canon",
    "docs/ADR",
    "docs/execution_tasks",
    ".github",  # optional but useful for governance integration
]

# Exclusions (determinism + avoid noise)
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".idea",
    ".vscode",
    "_archive",  # we typically avoid indexing archives
    "artifacts",  # index is about governance, not task evidence
}

EXCLUDE_FILE_PATTERNS = [
    r".*\.pyc$",
    r".*\.log$",
    r".*\.tmp$",
    r".*\.bak$",
]


LEVELS = [
    ("LEVEL 0", "Constitution", [
        "docs/_canon/AI_KERNEL.md",
    ]),
    ("LEVEL 1", "Protocols", [
        "docs/_canon/LANGUAGE_PROTOCOL.md",
        "docs/_canon/FAILSAFE_PROTOCOL.md",
        "docs/_canon/ARCH_REQUEST_DSL.md",
        "docs/_canon/AI_ARCH_EXEC_PROTOCOL.md",
        "docs/_canon/ARCHITECT_BOOTLOADER.md",
        "docs/_canon/ARCHITECT_HANDSHAKE.md",
        "docs/_canon/GOVERNANCE_MODEL.md",
        "docs/_canon/AGENT_BEHAVIOR.md",
    ]),
    ("LEVEL 2", "Prompts", [
        "docs/_canon/_prompts",
    ]),
    ("LEVEL 3", "Schemas", [
        "docs/_canon/_schemas",
    ]),
    ("LEVEL X", "Repo Governance (Selected)", [
        ".github/copilot-handshake.md",
        ".github/instructions",
        ".github/agents",
    ]),
    ("LEVEL Y", "Architecture Decisions & Execution", [
        "docs/ADR",
        "docs/execution_tasks",
    ]),
]


@dataclass(frozen=True)
class Entry:
    rel_path: str
    kind: str  # "file" or "dir"


def _compile_excludes() -> List[re.Pattern]:
    return [re.compile(p) for p in EXCLUDE_FILE_PATTERNS]


def _is_excluded_dir(path: Path) -> bool:
    return path.name in EXCLUDE_DIR_NAMES


def _is_excluded_file(path: Path, patterns: List[re.Pattern]) -> bool:
    s = str(path)
    return any(p.match(s) for p in patterns)


def _repo_rel(repo_root: Path, p: Path) -> str:
    return p.resolve().relative_to(repo_root.resolve()).as_posix()


def _scan_markdown_and_governance_files(repo_root: Path, roots: List[str]) -> List[Entry]:
    patterns = _compile_excludes()
    entries: List[Entry] = []

    for r in roots:
        root = (repo_root / r)
        if not root.exists():
            # roots can be optional; skip missing
            continue

        for cur_root, dirnames, filenames in os.walk(root):
            cur = Path(cur_root)

            # prune excluded dirs deterministically
            dirnames[:] = sorted([d for d in dirnames if d not in EXCLUDE_DIR_NAMES])

            if _is_excluded_dir(cur):
                continue

            for fn in sorted(filenames):
                p = cur / fn
                if _is_excluded_file(p, patterns):
                    continue

                # Include only "governance-relevant" filetypes
                if p.suffix.lower() in {".md", ".json", ".yml", ".yaml"}:
                    entries.append(Entry(rel_path=_repo_rel(repo_root, p), kind="file"))

    # stable sort
    entries = sorted(entries, key=lambda e: e.rel_path)
    return entries


def _group_entries(repo_root: Path, all_entries: List[Entry]) -> List[Tuple[str, str, List[Entry]]]:
    """
    For each LEVEL, collect entries that match the configured roots.
    Items are kept stable and unique (first match wins).
    """
    remaining = {e.rel_path: e for e in all_entries}
    grouped: List[Tuple[str, str, List[Entry]]] = []

    def take_prefix(prefix: str) -> List[Entry]:
        out: List[Entry] = []
        if prefix.endswith("/"):
            prefix2 = prefix
        else:
            prefix2 = prefix + "/"

        # exact file match
        if prefix in remaining:
            out.append(remaining.pop(prefix))

        # directory match
        for rp in sorted(list(remaining.keys())):
            if rp.startswith(prefix2):
                out.append(remaining.pop(rp))
        return out

    for level_name, title, paths in LEVELS:
        collected: List[Entry] = []
        for p in paths:
            collected.extend(take_prefix(p))
        grouped.append((level_name, title, collected))

    # We ignore any "remaining" not captured by configured LEVELS. This is intentional.
    return grouped


def _render_index(repo_root: Path, grouped: List[Tuple[str, str, List[Entry]]]) -> str:
    # compute a content hash over paths only (stable)
    hasher = hashlib.sha256()
    flat = []
    for _, _, entries in grouped:
        for e in entries:
            flat.append(e.rel_path)
    hasher.update("\n".join(flat).encode("utf-8"))
    idx_hash = hasher.hexdigest()[:16]

    lines: List[str] = []
    lines.append("# AI_GOVERNANCE_INDEX (AUTO-GENERATED)")
    lines.append("")
    lines.append("> DO NOT EDIT MANUALLY. Regenerate via `python scripts/_ia/generate_ai_governance_index.py --write`.")
    lines.append(f"> Index hash: `{idx_hash}`")
    lines.append("")
    lines.append("This index enumerates governance-relevant artifacts under the HB Track repository.")
    lines.append("")

    for level_name, title, entries in grouped:
        lines.append(f"## {level_name} — {title}")
        if not entries:
            lines.append("_No entries._")
            lines.append("")
            continue

        # Minimal, stable listing: bullets with relative paths
        for e in entries:
            lines.append(f"- `{e.rel_path}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _assert_required(repo_root: Path) -> None:
    missing = []
    for rel in CANON_REQUIRED:
        if not (repo_root / rel).exists():
            missing.append(rel)
    if missing:
        raise FileNotFoundError(f"Missing required canon files: {missing}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=REPO_ROOT_DEFAULT)
    ap.add_argument("--write", action="store_true", help="Write the generated index to docs/_canon/AI_GOVERNANCE_INDEX.md")
    ap.add_argument("--check", action="store_true", help="Fail if current file differs from generated output")
    args = ap.parse_args()

    if args.write and args.check:
        print("ERROR: choose only one of --write or --check", file=sys.stderr)
        return 3

    repo_root = Path(args.repo_root).resolve()

    try:
        _assert_required(repo_root)
        all_entries = _scan_markdown_and_governance_files(repo_root, SCAN_ROOTS)
        grouped = _group_entries(repo_root, all_entries)
        generated = _render_index(repo_root, grouped)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    out_path = repo_root / OUTPUT_INDEX

    if args.write:
        _write_text(out_path, generated)
        print(f"[OK] wrote {OUTPUT_INDEX}")
        return 0

    # default to --check if neither provided
    if not args.check and not args.write:
        args.check = True

    current = ""
    if out_path.exists():
        current = _read_text(out_path)

    if current != generated:
        print("[FAIL] AI_GOVERNANCE_INDEX.md is not up to date.", file=sys.stderr)
        print("Run: python scripts/_ia/generate_ai_governance_index.py --write", file=sys.stderr)
        return 2

    print("[OK] AI_GOVERNANCE_INDEX.md is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())