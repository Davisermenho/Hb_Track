#!/usr/bin/env python3
# scripts/_ia/lint_arch_request.py
"""
Regex-based linter for ARCH_REQUEST markdown.

Profiles:
- strict: enforce the newest DSL heading/header contract
- compat: accept legacy + current ARCH_REQUEST formats used in repo

Checks:
- ARCH_REQUEST header fields
- Required sections (strict exact headings or compat semantic headings)
- Presence of RFC2119 MUST language in objectives
- Prohibits opinion/hedging words inside normative sections
- SSOT paths must be repo-relative (no Windows absolute paths) unless explicitly allowed

Exit codes:
  0 = OK
  2 = DSL/structure violations
  3 = Normative language violations
  4 = SSOT/path violations
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple


ARCH_TITLE_ANY = re.compile(r"^#\s*ARCH_REQUEST(?:\s*[—:]\s*|\s+—\s+).+$", re.MULTILINE)

STRICT_HEADER_PATTERNS = [
    (
        re.compile(r"^#\s+ARCH_REQUEST\s+—\s+.+\s+\(v\d+\.\d+\.\d+\)\s*$", re.MULTILINE),
        "Missing/invalid strict title header: '# ARCH_REQUEST — ... (vX.Y.Z)'",
    ),
    (
        re.compile(r"^\*\*(TASK_ID|Task ID):\*\*\s+\S+", re.MULTILINE),
        "Missing strict TASK_ID line: '**TASK_ID:** ...' or '**Task ID:** ...'",
    ),
    (
        re.compile(r"^\*\*Determinism Score:\*\*\s+[1-5]/5", re.MULTILINE),
        "Missing strict Determinism Score line: '**Determinism Score:** N/5'",
    ),
    (
        re.compile(r"^\*\*(Priority|Prioridade):\*\*\s+\S+", re.MULTILINE),
        "Missing strict Priority line: '**Priority:** ...'",
    ),
]

COMPAT_HEADER_ALTERNATIVES = [
    (
        re.compile(r"^#\s+ARCH_REQUEST\s+—\s+.+$", re.MULTILINE),
        "header '# ARCH_REQUEST — ...'",
    ),
    (
        re.compile(r"^#\s+ARCH_REQUEST:\s+.+$", re.MULTILINE),
        "header '# ARCH_REQUEST: ...'",
    ),
]

COMPAT_ID_ALTERNATIVES = [
    (re.compile(r"^\*\*(ID|TASK_ID|Task ID):\*\*\s+\S+", re.MULTILINE), "ID/TASK_ID line"),
    (re.compile(r"^\*\*Canonical ID:\*\*\s+\S+", re.MULTILINE), "Canonical ID line"),
    (re.compile(r"^Task ID:\s+\S+", re.MULTILINE), "Task ID line"),
]

STRICT_REQUIRED_SECTIONS = [
    "## 1. CONTEXTO / PROBLEMA",
    "## 2. OBJETIVOS (MUST)",
    "## 3. SSOT & AUTORIDADE",
    "## 4. DELTA ESTRUTURAL",
    "## 5. PROTOCOLO DO EXECUTOR (MANDATÓRIO)",
    "## 6. ESPECIFICAÇÃO DO event.json",
    "## 7. GATES DE ACEITAÇÃO",
]

COMPAT_SECTION_RULES = [
    ("context", re.compile(r"^##\s+(?:(?:1[\.\)]\s+))?(?:CONTEXTO|CONTEXT)\b", re.IGNORECASE)),
    (
        "objectives",
        re.compile(
            r"^##\s+(?:(?:\d+[\.\)]\s+))?(?:OBJETIVOS(?:\s+\(MUST\))?|MUST\s+OBJECTIVES?)\b",
            re.IGNORECASE,
        ),
    ),
    ("ssot", re.compile(r"^##\s+(?:(?:\d+[\.\)]\s+))?SSOT\b", re.IGNORECASE)),
    (
        "gates",
        re.compile(
            r"^##\s+(?:(?:\d+[\.\)]\s+))?(?:GATES?(?:\s+DE\s+ACEITA[ÇC][ÃA]O)?)\b",
            re.IGNORECASE,
        ),
    ),
]

# Hedging/opinion words that must not appear in normative sections
HEDGING_WORDS = [
    r"\bacho\b",
    r"\btalvez\b",
    r"\bpode ser\b",
    r"\brecomendo\b",
    r"\bideal\b",
    r"\bna minha opinião\b",
    r"\bseria bom\b",
]

WINDOWS_ABS_PATH = re.compile(r"[A-Za-z]:\\")
UNC_PATH = re.compile(r"\\\\")  # \\server\share

RFC2119_WORD = re.compile(
    r"\bMUST\b|\bMUST NOT\b|\bSHALL\b|\bSHALL NOT\b|\bSHOULD\b|\bSHOULD NOT\b",
    re.IGNORECASE,
)


@dataclass
class LintIssue:
    file: str
    code: str
    message: str


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _extract_sections(md: str) -> Dict[str, str]:
    """
    Simple section extractor keyed by heading lines.
    Captures text until next '## ' heading (same level).
    """
    sections: Dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+.+$", md, flags=re.MULTILINE))
    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        sections[heading] = md[start:end]
    return sections


def _find_section_by_pattern(sections: Dict[str, str], pattern: Pattern[str]) -> Optional[Tuple[str, str]]:
    for heading, body in sections.items():
        if pattern.search(heading):
            return heading, body
    return None


def _enforce_headers(md: str, profile: str, path: Path, issues: List[LintIssue]) -> None:
    if profile == "strict":
        for pat, msg in STRICT_HEADER_PATTERNS:
            if not pat.search(md):
                issues.append(LintIssue(str(path), "ARCH_HDR", msg))
        return

    if not any(p.search(md) for p, _ in COMPAT_HEADER_ALTERNATIVES):
        accepted = " OR ".join(desc for _, desc in COMPAT_HEADER_ALTERNATIVES)
        issues.append(LintIssue(str(path), "ARCH_HDR", f"Missing ARCH_REQUEST title ({accepted})"))

    if not any(p.search(md) for p, _ in COMPAT_ID_ALTERNATIVES):
        accepted = " OR ".join(desc for _, desc in COMPAT_ID_ALTERNATIVES)
        issues.append(LintIssue(str(path), "ARCH_HDR", f"Missing ARCH_REQUEST identifier ({accepted})"))


def _enforce_sections(
    sections: Dict[str, str],
    profile: str,
    path: Path,
    issues: List[LintIssue],
) -> Dict[str, Tuple[str, str]]:
    section_hits: Dict[str, Tuple[str, str]] = {}

    if profile == "strict":
        for heading in STRICT_REQUIRED_SECTIONS:
            if heading not in sections:
                issues.append(
                    LintIssue(str(path), "ARCH_SEC", f"Missing required section heading: '{heading}'")
                )
            else:
                key = heading.lower()
                section_hits[key] = (heading, sections[heading])
        return section_hits

    for key, pattern in COMPAT_SECTION_RULES:
        hit = _find_section_by_pattern(sections, pattern)
        if not hit:
            issues.append(
                LintIssue(
                    str(path),
                    "ARCH_SEC",
                    f"Missing required semantic section for '{key}' (compat profile).",
                )
            )
            continue
        section_hits[key] = hit
    return section_hits


def _enforce_normative(
    path: Path,
    section_hits: Dict[str, Tuple[str, str]],
    profile: str,
    issues: List[LintIssue],
) -> None:
    if profile == "strict":
        obj_key = "## 2. OBJETIVOS (MUST)".lower()
        gates_key = "## 7. GATES DE ACEITAÇÃO".lower()
        obj = section_hits.get(obj_key)
        gates = section_hits.get(gates_key)
    else:
        obj = section_hits.get("objectives")
        gates = section_hits.get("gates")

    if obj:
        obj_heading, obj_text = obj
        if not RFC2119_WORD.search(obj_text):
            issues.append(
                LintIssue(
                    str(path),
                    "ARCH_NORM",
                    f"Section '{obj_heading}' must contain RFC2119 keywords (MUST/SHALL/etc.).",
                )
            )
        for pattern in HEDGING_WORDS:
            if re.search(pattern, obj_text, flags=re.IGNORECASE):
                issues.append(
                    LintIssue(
                        str(path),
                        "ARCH_HEDGE",
                        f"Hedging/opinion forbidden in '{obj_heading}': pattern '{pattern}'",
                    )
                )

    if gates:
        gates_heading, gates_text = gates
        for pattern in HEDGING_WORDS:
            if re.search(pattern, gates_text, flags=re.IGNORECASE):
                issues.append(
                    LintIssue(
                        str(path),
                        "ARCH_HEDGE",
                        f"Hedging/opinion forbidden in '{gates_heading}': pattern '{pattern}'",
                    )
                )


def _enforce_ssot_paths(
    path: Path,
    section_hits: Dict[str, Tuple[str, str]],
    profile: str,
    allow_abs_paths: bool,
    issues: List[LintIssue],
) -> None:
    if allow_abs_paths:
        return

    if profile == "strict":
        ssot = section_hits.get("## 3. SSOT & AUTORIDADE".lower())
    else:
        ssot = section_hits.get("ssot")

    if not ssot:
        return

    ssot_heading, ssot_text = ssot
    if WINDOWS_ABS_PATH.search(ssot_text) or UNC_PATH.search(ssot_text):
        issues.append(
            LintIssue(
                str(path),
                "ARCH_PATH",
                f"Section '{ssot_heading}' contains absolute/UNC Windows paths. Use repo-relative paths.",
            )
        )


def lint_file(path: Path, profile: str, allow_abs_paths: bool) -> List[LintIssue]:
    md = _read_text(path)
    issues: List[LintIssue] = []

    _enforce_headers(md, profile=profile, path=path, issues=issues)
    sections = _extract_sections(md)
    section_hits = _enforce_sections(sections, profile=profile, path=path, issues=issues)
    _enforce_normative(path=path, section_hits=section_hits, profile=profile, issues=issues)
    _enforce_ssot_paths(
        path=path,
        section_hits=section_hits,
        profile=profile,
        allow_abs_paths=allow_abs_paths,
        issues=issues,
    )
    return issues


def classify_exit_code(issues: List[LintIssue]) -> int:
    if not issues:
        return 0
    codes = {i.code for i in issues}
    if "ARCH_PATH" in codes:
        return 4
    if "ARCH_NORM" in codes or "ARCH_HEDGE" in codes:
        return 3
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Single file to lint")
    ap.add_argument("--glob", dest="glob_pattern", help="Glob pattern for files (e.g., 'docs/**/AR-*.md')")
    ap.add_argument(
        "--profile",
        choices=["strict", "compat"],
        default="compat",
        help="Lint profile. 'compat' accepts legacy ARCH_REQUEST formats in the repo.",
    )
    ap.add_argument(
        "--skip-non-arch",
        action="store_true",
        help="Skip files that do not contain an ARCH_REQUEST title header.",
    )
    ap.add_argument("--allow-absolute-paths", action="store_true", help="Allow Windows absolute paths in SSOT")
    ap.add_argument("--verbose", action="store_true", help="Verbose output (accepted for workflow compatibility)")
    args = ap.parse_args()

    targets: List[str] = []
    if args.file:
        targets = [args.file]
    elif args.glob_pattern:
        targets = glob.glob(args.glob_pattern, recursive=True)
    else:
        print("ERROR: provide --file or --glob", file=sys.stderr)
        return 2

    if not targets:
        print("[OK] No files matched. Nothing to lint.")
        return 0

    all_issues: List[LintIssue] = []
    linted = 0
    skipped = 0
    for t in sorted(set(targets)):
        p = Path(t)
        if not p.exists() or not p.is_file():
            continue
        md = _read_text(p)
        if args.skip_non_arch and not ARCH_TITLE_ANY.search(md):
            skipped += 1
            continue
        linted += 1
        all_issues.extend(
            lint_file(
                p,
                profile=args.profile,
                allow_abs_paths=args.allow_absolute_paths,
            )
        )

    if args.verbose:
        print(f"[INFO] Linted files: {linted}; skipped non-ARCH files: {skipped}")

    if all_issues:
        for issue in all_issues:
            print(f"{issue.file}: {issue.code}: {issue.message}", file=sys.stderr)

    rc = classify_exit_code(all_issues)
    if rc == 0:
        print("[OK] ARCH_REQUEST lint passed.")
    else:
        print(f"[FAIL] ARCH_REQUEST lint failed (exit {rc}).", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
