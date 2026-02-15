#!/usr/bin/env python3
"""
HB Track — policy_lib.py (Core deterministic policy library)

Central library for scripts governance:
- Load SSOT (YAML)
- Validate schema + semantics
- Render DERIVED (Markdown)
- Compute hashes (manifest)
- Validate scripts against policy (headers, prefixes, side-effects)

Exit codes convention:
  0 = OK
  2 = POLICY_VIOLATION
  3 = HARNESS_ERROR

Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ----------------------------
# Constants and Rule IDs
# ----------------------------
VERSION = "1.0.0"

# ----------------------------
# Canonical paths (SSOT contract)
# ----------------------------
# These paths are PART OF THE CONTRACT between SSOT, DERIVED, gates, and CI.
# Changes here require CI workflow update.
#
# Path rationale:
# - SSOT: scripts/_policy/scripts.policy.yaml (versioned YAML policy)
# - DERIVED: docs/_canon/_agent/SCRIPTS_classification.md (canonized MD for agents)
#   Note: _agent indicates "documentation for AI agents" (not ephemeral)
# - MANIFEST: scripts/_policy/policy.manifest.json (evidence with SHA256 hashes)
# - HEURISTICS: scripts/_policy/side_effects_heuristics.yaml (auxiliary policy)

SSOT_YAML_RELPATH = "scripts/_policy/scripts.policy.yaml"
DERIVED_MD_RELPATH = "docs/_canon/_agent/SCRIPTS_classification.md"
MANIFEST_JSON_RELPATH = "scripts/_policy/policy.manifest.json"
HEURISTICS_YAML_RELPATH = "scripts/_policy/side_effects_heuristics.yaml"

# Rule catalog (stable IDs for exceptions and reporting)
RULE_IDS = {
    "HB001": "PATH_NOT_UNDER_SCRIPTS",
    "HB002": "TAXONOMY_FOLDER_INVALID",
    "HB003": "PREFIX_MISMATCH",
    "HB004": "REQUIRED_HEADERS_MISSING",
    "HB005": "HEADER_KIND_MISMATCH",
    "HB006": "SIDE_EFFECTS_PROHIBITED_FOR_KIND",
    "HB007": "SIDE_EFFECTS_UNDECLARED",
    "HB008": "RUN_REFERENCES_TEMP",
    "HB009": "TEMP_TRACKED_IN_GIT",
    "HB010": "DERIVED_MD_DRIFT",
    "HB011": "DERIVED_MD_CANONICAL_PATH_CASE",
    "HB012": "MANIFEST_HASH_MISMATCH",
    "HB013": "EXCEPTION_EXPIRED_OR_INVALID",
}

# Deterministic ordering for taxonomy
TAXONOMY_PRECEDENCE = [
    "reset",
    "migrate",
    "fixes",
    "seeds",
    "generate",
    "checks",
    "diagnostics",
    "ops",
    "temp",
    "artifacts",
    "run",
]

# Valid vocabulary
VALID_KINDS = [
    "CHECK",
    "DIAGNOSTIC",
    "FIX",
    "GENERATE",
    "MIGRATE",
    "OPS",
    "RESET",
    "SEED",
    "RUNNER",
    "TEMP",
    "ARTIFACT",
]

VALID_EFFECTS = [
    "NONE",
    "DB_READ",
    "DB_WRITE",
    "FS_READ",
    "FS_WRITE",
    "ENV_WRITE",
    "NET",
    "PROC_START_STOP",
    "DESTRUCTIVE",
]

VALID_EXTS_DEFAULT = [".py", ".ps1", ".sql"]

# Canonical prefixes for script-candidate detection
CANON_PREFIXES = ("check_", "diag_", "fix_", "gen_", "mig_", "ops_", "reset_", "seed_", "run_", "tmp_")

# Excepted files (not subject to header validation)
EXCEPT_FILES = {"README.md", ".gitignore", "__init__.py"}

# Required headers per script
REQUIRED_HEADERS = [
    "HB_SCRIPT_KIND",
    "HB_SCRIPT_SCOPE",
    "HB_SCRIPT_SIDE_EFFECTS",
    "HB_SCRIPT_IDEMPOTENT",
    "HB_SCRIPT_ENTRYPOINT",
    "HB_SCRIPT_OUTPUTS",
]

OPTIONAL_HEADERS = [
    "HB_SCRIPT_INPUTS",
    "HB_SCRIPT_RISK",
    "HB_SCRIPT_ROLLBACK",
]

# Derived file header
DERIVED_PREAMBLE = """<!--
DERIVED FILE — DO NOT EDIT BY HAND

This Markdown is derived from the SSOT policy:
- scripts/_policy/scripts.policy.yaml
Validated by:
- scripts/_policy/scripts.policy.schema.json

Edits MUST be applied to scripts.policy.yaml, then the generator MUST re-render this file.
-->
"""


# ----------------------------
# YAML/JSON loading
# ----------------------------
def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML deterministically. Fails with HARNESS_ERROR if missing deps."""
    try:
        import yaml  # type: ignore
    except Exception:
        raise RuntimeError(
            "Missing dependency: PyYAML. Install with: pip install pyyaml"
        )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root MUST be an object/map.")
    return data


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON deterministically."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# Schema validation
# ----------------------------
def validate_schema(instance: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Returns list of error strings. Empty list means OK.
    Uses jsonschema if available; otherwise fails deterministically.
    """
    try:
        import jsonschema  # type: ignore
    except Exception:
        return ["Missing dependency: jsonschema. Install with: pip install jsonschema"]

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: e.json_path):
        path = err.json_path or "$"
        errors.append(f"{path}: {err.message}")
    return errors


# ----------------------------
# Deterministic helpers
# ----------------------------
def sorted_keys(d: Dict[str, Any]) -> List[str]:
    """Stable case-insensitive sort for dict keys."""
    return sorted(d.keys(), key=lambda s: (s.lower(), s))


def norm_ws(s: str) -> str:
    """Normalize whitespace: CRLF → LF, trailing newlines trimmed."""
    return s.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def md_codeblock(content: str) -> str:
    """Wrap content in Markdown code block."""
    return f"```\n{content.rstrip()}\n```"


def require_str(d: Dict[str, Any], key: str) -> str:
    """Require non-empty string field."""
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"Missing/invalid required string field: {key}")
    return v.strip()


def require_list_of_str(d: Dict[str, Any], key: str) -> List[str]:
    """Require list of strings."""
    v = d.get(key)
    if not isinstance(v, list) or not all(isinstance(i, str) for i in v):
        raise ValueError(f"Missing/invalid required list[str] field: {key}")
    return [i.strip() for i in v]


def norm_path(p: str) -> str:
    """
    Normalize path to POSIX format (/) for deterministic comparison.
    Removes './' prefix if present.
    """
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def compute_file_hash(path: Path) -> str:
    """
    Compute SHA256 hash of file (deterministic, EOL-normalized).
    
    For text files (.py, .yaml, .md, .json, .ps1), normalizes CRLF → LF
    before hashing to ensure cross-platform consistency.
    """
    if not path.exists():
        return ""
    
    # For known text files, normalize EOL before hashing
    text_exts = {".py", ".yaml", ".yml", ".md", ".json", ".ps1", ".txt"}
    if path.suffix.lower() in text_exts:
        try:
            content = path.read_text(encoding="utf-8")
            # Normalize: CRLF → LF, trailing whitespace
            content_normalized = content.replace("\r\n", "\n").replace("\r", "\n")
            # Hash normalized UTF-8 bytes
            sha = hashlib.sha256(content_normalized.encode("utf-8"))
            return sha.hexdigest()
        except Exception:
            # Fallback to binary if text read fails
            pass
    
    # Binary files: hash as-is
    sha = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


# ----------------------------
# Semantic validation (beyond JSON schema)
# ----------------------------
def semantic_validate(policy: Dict[str, Any]) -> List[str]:
    """Validate policy semantics. Returns list of error strings."""
    errs: List[str] = []

    # Basic spec presence
    if "spec" not in policy or not isinstance(policy["spec"], dict):
        errs.append("spec: missing or not an object")
        return errs

    taxonomy = policy.get("taxonomy", {})
    if not isinstance(taxonomy, dict):
        errs.append("taxonomy: missing or not an object")
        return errs

    classification = taxonomy.get("classification", {})
    if not isinstance(classification, dict):
        errs.append("taxonomy.classification: missing or not an object")
        return errs

    # Precedence order validation (if present)
    precedence = classification.get("precedence_order", [])
    if not isinstance(precedence, list):
        errs.append("taxonomy.classification.precedence_order: must be list")

    # Validate side_effects vocabulary
    effects = taxonomy.get("side_effects", VALID_EFFECTS)
    if not isinstance(effects, list) or not all(isinstance(x, str) for x in effects):
        errs.append("taxonomy.side_effects: invalid list[str]")

    # TODO: Add more semantic rules as needed (folder consistency, etc.)
    return errs


# ----------------------------
# Markdown rendering (deterministic)
# ----------------------------
def render_md(policy: Dict[str, Any]) -> str:
    """
    Render deterministic Markdown from policy YAML.
    
    Determinism guarantees:
    - Stable ordering (by precedence, then alphabetical)
    - No timestamps in MD (only in manifest)
    - Normalized EOL (LF)
    - No locale/timezone dependencies
    """
    spec = policy.get("spec", {})
    version = require_str(spec, "version")
    date = spec.get("date", "").strip() if isinstance(spec.get("date"), str) else ""
    status = require_str(spec, "status")
    title = spec.get("title", "HB Track Scripts Classification (BCP14)")

    taxonomy = policy.get("taxonomy", {})
    classification = taxonomy.get("classification", {})
    precedence_order = classification.get("precedence_order", TAXONOMY_PRECEDENCE)

    lines: List[str] = []
    lines.append(DERIVED_PREAMBLE.strip())
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Version:** {version}  ")
    if date:
        lines.append(f"**Date:** {date}  ")
    lines.append(f"**Status:** {status}  ")
    lines.append("**SSOT:** `scripts/_policy/scripts.policy.yaml`  ")
    lines.append("**Schema:** `scripts/_policy/scripts.policy.schema.json`  ")
    lines.append("**Derived:** `docs/_canon/_agent/SCRIPTS_classification.md` (this file)")
    lines.append("")

    lines.append("## 1. Objective")
    lines.append("")
    lines.append(
        "This specification defines a **deterministic classification system** for ANY script "
        "created in this repository, using only:"
    )
    lines.append("")
    lines.append("1. Script intent (KIND)")
    lines.append("2. Script side-effects (observable operations)")
    lines.append("3. Fixed folder taxonomy + naming rules")
    lines.append("")
    lines.append("A script that complies with this spec SHALL have exactly **one valid placement** "
                 "(folder + sub-scope) and **one valid name pattern**.")
    lines.append("")

    lines.append("## 2. Taxonomy (Top-Level Categories)")
    lines.append("")
    lines.append("Deterministic precedence order (highest wins):")
    lines.append("")
    lines.append(md_codeblock(" > ".join([x.upper() for x in precedence_order])))
    lines.append("")

    lines.append("## 3. Classification Dimensions")
    lines.append("")
    lines.append(f"**KIND:** {', '.join(VALID_KINDS)}")
    lines.append("")
    lines.append(f"**SIDE_EFFECTS:** {', '.join(VALID_EFFECTS)}")
    lines.append("")
    lines.append(f"**Extensions:** {', '.join(VALID_EXTS_DEFAULT)}")
    lines.append("")

    lines.append("## 4. Required Headers")
    lines.append("")
    lines.append("Every script MUST include these metadata fields:")
    lines.append("")
    for h in REQUIRED_HEADERS:
        lines.append(f"- `{h}`")
    lines.append("")
    lines.append("Optional fields:")
    lines.append("")
    for h in OPTIONAL_HEADERS:
        lines.append(f"- `{h}`")
    lines.append("")

    lines.append("## 5. Naming Convention")
    lines.append("")
    lines.append("**Pattern:** `<prefix><scope>__<action>[_qualifier].<ext>`")
    lines.append("")
    lines.append("**Prefix per category:**")
    lines.append("")
    lines.append("| Category | Prefix |")
    lines.append("| --- | --- |")
    lines.append("| `checks/` | `check_` |")
    lines.append("| `diagnostics/` | `diag_` |")
    lines.append("| `fixes/` | `fix_` |")
    lines.append("| `generate/` | `gen_` |")
    lines.append("| `migrate/` | `mig_` |")
    lines.append("| `ops/` | `ops_` |")
    lines.append("| `reset/` | `reset_` |")
    lines.append("| `run/` | `run_` |")
    lines.append("| `seeds/` | `seed_` |")
    lines.append("| `temp/` | `tmp_` |")
    lines.append("")

    lines.append("## 6. Artifacts Policy")
    lines.append("")
    lines.append("`scripts/artifacts/` is **OUTPUT-ONLY**, MUST be gitignored (except README), "
                 "and MUST NOT be used as SSOT input.")
    lines.append("")

    lines.append("## 7. Temp Policy")
    lines.append("")
    lines.append("`scripts/temp/` is **quarantine**, MUST be gitignored, and MUST NOT be "
                 "referenced by `scripts/run/` wrappers.")
    lines.append("")

    lines.append("## 8. Determinism Acceptance Criteria")
    lines.append("")
    lines.append("This system is deterministic if and only if:")
    lines.append("")
    lines.append("1. Any new script's category is uniquely determined by constraints + precedence")
    lines.append("2. Misplacements are mechanically detectable by gates")
    lines.append("3. This Markdown matches the SSOT YAML (drift forbidden)")
    lines.append("")

    return norm_ws("\n".join(lines))


# ----------------------------
# Heuristics: Side-effects detection
# ----------------------------
def load_heuristics(heuristics_path: Path) -> Dict[str, Any]:
    """Load side-effects heuristics YAML."""
    if not heuristics_path.exists():
        return {"detect": {}}
    return load_yaml(heuristics_path)


def is_comment_line(line: str, ext: str) -> bool:
    """
    Detect if line is a comment (simple, doesn't parse full language).
    Reduces false positives from examples in comments/docstrings.
    """
    stripped = line.strip()
    if not stripped:
        return True  # Empty lines don't match patterns anyway
    
    if ext in [".ps1", ".py"]:
        return stripped.startswith("#")
    elif ext == ".sql":
        # Single-line comment
        if stripped.startswith("--"):
            return True
    return False


def iter_effective_lines(content: str, ext: str):
    """
    Yield non-comment lines for pattern matching.
    Filters out comments to reduce false positives.
    """
    in_sql_block = False
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue

        if ext == ".sql":
            # Block comments /* ... */
            if in_sql_block:
                if "*/" in s:
                    in_sql_block = False
                continue
            if s.startswith("/*"):
                if "*/" not in s:
                    in_sql_block = True
                continue
            if s.startswith("--"):
                continue
            yield line
            continue

        # .py and .ps1
        if s.startswith("#"):
            continue
        yield line


def _is_select_only_execute_text(content: str) -> bool:
    """
    High-priority check for execute(text("SELECT...")) patterns.
    Detects deterministically: execute(text("SELECT ... ")) where SQL is SELECT-only.
    Returns True if confirmed SELECT-only SQL in text() literal.
    """
    # Pattern: execute(text("""...""")) or execute(text('...')) with SQL SELECT
    # Captures multi-line raw strings and validates no write operations
    pattern = r'(?i)\.execute\s*\(\s*text\s*\(\s*["\']'
    
    if not re.search(pattern, content, re.IGNORECASE):
        return False
    
    # Extract execute(text(...)) blocks
    # Match: text("...") or text("""...""")
    sql_pattern = r'\.execute\s*\(\s*text\s*\(\s*"""(.*?)"""|text\s*\(\s*["\']([^"\']*)["\']'
    matches = re.finditer(sql_pattern, content, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        sql_str = match.group(1) or match.group(2) or ""
        if not sql_str.strip():
            continue
        
        # Normalize SQL (remove comments, extra whitespace)
        sql_normalized = re.sub(r'--.*$', '', sql_str, flags=re.MULTILINE)  # Remove SQL comments
        sql_normalized = re.sub(r'#.*$', '', sql_normalized, flags=re.MULTILINE)  # Remove Python comments
        sql_normalized = re.sub(r'/\*.*?\*/', '', sql_normalized, flags=re.DOTALL)  # Remove block comments
        
        # Check for DML (write operations)
        write_keywords = [r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bCREATE\b', 
                         r'\bALTER\b', r'\bDROP\b', r'\bTRUNCATE\b', r'\bMERGE\b']
        has_write = any(re.search(kw, sql_normalized, re.IGNORECASE) for kw in write_keywords)
        
        if has_write:
            return False  # Contains write operations, not SELECT-only
        
        # Check for SELECT or WITH (read-only operations)
        if re.search(r'^\s*(SELECT|WITH)\b', sql_normalized, re.IGNORECASE):
            return True  # Confirmed SELECT-only
    
    return False


def detect_side_effects(
    script_path: Path, heuristics: Dict[str, Any]
) -> Set[str]:
    """
    Detect side-effects from script content using regex heuristics.
    Returns set of detected effect names (e.g., {"DB_WRITE", "FS_WRITE"}).
    Filters out comments to reduce false positives.
    
    ** PRIORITY RULE (HB006 override): **
    If execute(text("SELECT...")) is detected (SELECT-only SQL), mark as DB_READ
    and exclude DB_WRITE to prevent false HB006 violation in checks/diagnostics.
    """
    if not script_path.exists():
        return set()

    ext = script_path.suffix.lower()
    content = script_path.read_text(encoding="utf-8", errors="ignore")

    detect = heuristics.get("detect", {})
    lang_map = {
        ".py": "python",
        ".ps1": "powershell",
        ".sql": "sql",
    }
    lang = lang_map.get(ext)
    if not lang:
        return set()

    lang_rules = detect.get(lang, {})
    detected: Set[str] = set()

    # PRIORITY RULE: Check for execute(text("SELECT...")) FIRST (Python only)
    if lang == "python" and _is_select_only_execute_text(content):
        # Confirmed SELECT-only: mark DB_READ, exclude DB_WRITE
        detected.add("DB_READ")
        # Do NOT add DB_WRITE (even if generic pattern matches)
        # Continue checking other patterns (FS_*, etc.)
        skip_db_write = True
    else:
        skip_db_write = False

    # Apply heuristic patterns (with skip override for DB_WRITE if needed)
    for line in iter_effective_lines(content, ext):
        for effect, patterns in lang_rules.items():
            # Skip DB_WRITE if we already confirmed SELECT-only
            if skip_db_write and effect == "DB_WRITE":
                continue
            
            if not isinstance(patterns, list):
                continue
            for pattern in patterns:
                if isinstance(pattern, str):
                    try:
                        if re.search(pattern, line, re.IGNORECASE):
                            detected.add(effect)
                            break  # One match per effect is enough
                    except Exception:
                        pass  # Skip invalid regex

    return detected


# ----------------------------
# Policy validation (scripts against policy)
# ----------------------------
def has_script_header(script_path: Path) -> bool:
    """
    Check if script has HB_SCRIPT_KIND header in first 50 lines.
    Used for R1.3 (POLICY-E_UNTAGGED_SCRIPT) validation.
    """
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines()[:50]:
            if "HB_SCRIPT_KIND" in line:
                return True
        return False
    except Exception:
        return False


def is_script_candidate(filename: str, script_path: Path) -> bool:
    """
    Determine if file is a script-candidate (has canonical prefix OR header).
    """
    if filename.startswith(CANON_PREFIXES):
        return True
    return has_script_header(script_path)


def validate_scripts(
    repo_root: Path,
    policy: Dict[str, Any],
    heuristics: Dict[str, Any],
) -> List[Tuple[str, str, str]]:
    """
    Validate all scripts under scripts/ against policy.
    
    Returns list of violations: (rule_id, script_path, message)
    """
    violations: List[Tuple[str, str, str]] = []
    scripts_dir = repo_root / "scripts"

    if not scripts_dir.exists():
        return violations

    # A1: Get tracked files using git ls-files -z (deterministic, portable)
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", "scripts"],
            cwd=repo_root,
            capture_output=True,
            text=False,  # Binary for NUL-separated output
            check=False,
        )
        if result.returncode == 0:
            # Split by NUL, decode UTF-8, filter empty
            paths_raw = result.stdout.decode("utf-8", errors="replace").split("\0")
            tracked = [
                repo_root / norm_path(p.strip())
                for p in paths_raw
                if p.strip()
            ]
        else:
            # Fallback: scan filesystem (less reliable)
            tracked = list(scripts_dir.rglob("*"))
    except Exception:
        tracked = list(scripts_dir.rglob("*"))

    # Filter to executable scripts
    script_files = [
        p for p in tracked
        if p.is_file() and p.suffix.lower() in VALID_EXTS_DEFAULT
    ]

    for script_path in script_files:
        # A2: Normalize path completely
        rel_path = norm_path(str(script_path.relative_to(repo_root)))

        # Rule HB001: Must be under scripts/
        if not rel_path.startswith("scripts/"):
            violations.append(("HB001", rel_path, "Path not under scripts/"))
            continue

        # Rule HB009: temp/ must not be tracked
        if "/temp/" in rel_path or rel_path.startswith("scripts/temp/"):
            violations.append(("HB009", rel_path, "scripts/temp/ must be gitignored"))
            continue

        # Determine category from path
        parts = rel_path.split("/")
        if len(parts) < 2:
            continue  # Skip scripts/ root files

        category = parts[1]  # e.g., "checks", "fixes", etc.

        # Rule HB002: Valid taxonomy folder
        if category not in TAXONOMY_PRECEDENCE and category not in ["_policy", "_lib"]:
            violations.append(("HB002", rel_path, f"Invalid taxonomy folder: {category}"))
            continue

        # Skip policy/lib internals
        if category in ["_policy", "_lib"]:
            continue

        # R1.3: POLICY-E_UNTAGGED_SCRIPT (detect untagged scripts in operational categories)
        # Any .py/.ps1/.sql file in operational category MUST be a script-candidate
        if category in ["checks", "diagnostics", "fixes", "generate", "migrate", "ops", "reset", "run", "seeds", "temp"]:
            if script_path.name not in EXCEPT_FILES:
                if script_path.suffix.lower() in VALID_EXTS_DEFAULT:
                    if not is_script_candidate(script_path.name, script_path):
                        violations.append(
                            ("POLICY-E_UNTAGGED_SCRIPT", rel_path,
                             "File in operational category lacks canonical prefix and HB_SCRIPT_KIND header")
                        )
                        # Don't continue - still validate other rules for reporting

        # Rule HB003: Prefix mismatch
        expected_prefix = get_expected_prefix(category)
        if expected_prefix and not script_path.name.startswith(expected_prefix):
            violations.append(
                ("HB003", rel_path, f"Expected prefix '{expected_prefix}', got '{script_path.name}'")
            )

        # Rule HB004 & HB005: Headers validation
        header_violations = validate_headers(script_path, category)
        for hv in header_violations:
            violations.append(hv)

        # Rule HB006 & HB007: Side-effects validation
        se_violations = validate_side_effects(script_path, category, heuristics)
        for sev in se_violations:
            violations.append(sev)

        # Rule HB008: run/ must not reference temp/
        if category == "run":
            if references_temp(script_path):
                violations.append(
                    ("HB008", rel_path, "scripts/run/ must not reference scripts/temp/")
                )

    # A3: Sort violations deterministically (by path, then code, then details)
    violations_sorted = sorted(
        violations,
        key=lambda v: (v[1], v[0], v[2])  # path, code, details
    )
    return violations_sorted


def get_expected_prefix(category: str) -> str:
    """Get expected filename prefix for a category."""
    prefix_map = {
        "checks": "check_",
        "diagnostics": "diag_",
        "fixes": "fix_",
        "generate": "gen_",
        "migrate": "mig_",
        "ops": "ops_",
        "reset": "reset_",
        "run": "run_",
        "seeds": "seed_",
        "temp": "tmp_",
    }
    return prefix_map.get(category, "")


def validate_headers(script_path: Path, category: str) -> List[Tuple[str, str, str]]:
    """Validate required headers in script. Returns list of violations."""
    violations: List[Tuple[str, str, str]] = []
    rel_path = script_path.as_posix()

    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    # Extract headers (flexible: accepts # or -- leader, = or : separator)
    headers = {}
    for line in content.splitlines()[:100]:  # Check first 100 lines
        match = re.match(r"^\s*(?:(#|--)\s*)?HB_SCRIPT_(\w+)\s*[:=]\s*(.+?)\s*$", line)
        if match:
            key = f"HB_SCRIPT_{match.group(2)}"  # group(2) = field name
            value = match.group(3).strip()  # group(3) = value
            headers[key] = value

    # Normalize IDEMPOTENT values (TRUE->YES, FALSE->NO)
    if "HB_SCRIPT_IDEMPOTENT" in headers:
        raw = headers["HB_SCRIPT_IDEMPOTENT"].strip().upper()
        normalized = {"TRUE": "YES", "FALSE": "NO"}.get(raw, raw)
        if normalized not in {"YES", "NO", "CONDITIONAL"}:
            violations.append(("HB004", rel_path, f"Invalid IDEMPOTENT value: {raw} (expected YES/NO/CONDITIONAL)"))
        else:
            headers["HB_SCRIPT_IDEMPOTENT"] = normalized

    # Check required headers
    for req in REQUIRED_HEADERS:
        if req not in headers:
            violations.append(("HB004", rel_path, f"Missing required header: {req}"))

    # Rule HB005: KIND must match category
    kind = headers.get("HB_SCRIPT_KIND", "").upper()
    expected_kind = get_expected_kind(category)
    if kind and expected_kind and kind != expected_kind:
        violations.append(
            ("HB005", rel_path, f"KIND mismatch: header='{kind}', expected='{expected_kind}'")
        )

    return violations


def get_expected_kind(category: str) -> str:
    """Get expected KIND for a category."""
    kind_map = {
        "checks": "CHECK",
        "diagnostics": "DIAGNOSTIC",
        "fixes": "FIX",
        "generate": "GENERATE",
        "migrate": "MIGRATE",
        "ops": "OPS",
        "reset": "RESET",
        "run": "RUNNER",
        "seeds": "SEED",
        "temp": "TEMP",
    }
    return kind_map.get(category, "")


def validate_side_effects(
    script_path: Path, category: str, heuristics: Dict[str, Any]
) -> List[Tuple[str, str, str]]:
    """Validate side-effects against category constraints."""
    violations: List[Tuple[str, str, str]] = []
    rel_path = script_path.as_posix()

    # Detect side-effects
    detected = detect_side_effects(script_path, heuristics)

    # Define prohibited side-effects per category
    prohibited_map = {
        "checks": {"DB_WRITE", "FS_WRITE", "ENV_WRITE", "DESTRUCTIVE"},
        "diagnostics": {"DB_WRITE", "FS_WRITE", "ENV_WRITE", "DESTRUCTIVE"},
    }

    prohibited = prohibited_map.get(category, set())
    violations_found = detected.intersection(prohibited)

    if violations_found:
        violations.append(
            ("HB006", rel_path, f"Prohibited side-effects detected: {', '.join(sorted(violations_found))}")
        )

    return violations


def references_temp(script_path: Path) -> bool:
    """Check if script references scripts/temp/ (for run/ scripts)."""
    try:
        content = script_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # Normalize paths and check for references
    content_normalized = content.replace("\\", "/")
    patterns = [
        r"scripts[/\\]temp[/\\]",
        r"['\"]temp[/\\]",
        r"\.\..*temp[/\\]",
    ]

    for pattern in patterns:
        if re.search(pattern, content_normalized, re.IGNORECASE):
            return True

    return False


# ----------------------------
# Manifest operations
# ----------------------------
def generate_manifest(repo_root: Path) -> Dict[str, Any]:
    """Generate policy manifest with hashes and metadata."""
    import datetime

    ssot_path = repo_root / SSOT_YAML_RELPATH
    heuristics_path = repo_root / HEURISTICS_YAML_RELPATH
    derived_path = repo_root / DERIVED_MD_RELPATH

    manifest = {
        "schema_version": "1.0.0",
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "canonical_generator": "scripts/_policy/render_policy_md.py",
        "generator_version": VERSION,
        "hashes": {
            "scripts.policy.yaml": compute_file_hash(ssot_path),
            "side_effects_heuristics.yaml": compute_file_hash(heuristics_path),
            "SCRIPTS_classification.md": compute_file_hash(derived_path),
        },
    }

    return manifest


def validate_manifest(repo_root: Path, manifest: Dict[str, Any]) -> List[str]:
    """Validate manifest hashes. Returns list of error messages."""
    errors: List[str] = []

    ssot_path = repo_root / SSOT_YAML_RELPATH
    heuristics_path = repo_root / HEURISTICS_YAML_RELPATH
    derived_path = repo_root / DERIVED_MD_RELPATH

    hashes = manifest.get("hashes", {})

    # Check each file hash
    files = {
        "scripts.policy.yaml": ssot_path,
        "side_effects_heuristics.yaml": heuristics_path,
        "SCRIPTS_classification.md": derived_path,
    }

    for name, path in files.items():
        expected = hashes.get(name, "")
        actual = compute_file_hash(path)
        if expected != actual:
            errors.append(f"HB012: Hash mismatch for {name}: expected={expected[:16]}..., actual={actual[:16]}...")

    return errors


# ----------------------------
# Exception handling
# ----------------------------
def load_exceptions(policy: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Load exceptions from policy.
    Returns dict: script_path -> {rule_id, reason, expires_on, ticket}
    """
    exceptions_list = policy.get("exceptions", [])
    if not isinstance(exceptions_list, list):
        return {}

    result = {}
    for exc in exceptions_list:
        if not isinstance(exc, dict):
            continue
        script = exc.get("script")
        if script:
            result[script] = exc

    return result


def validate_exceptions(exceptions: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate exceptions: expiration, ticket presence. Returns errors."""
    import datetime

    errors: List[str] = []
    today = datetime.date.today()

    for script, exc in exceptions.items():
        rule_id = exc.get("rule_id")
        expires_on = exc.get("expires_on")
        ticket = exc.get("ticket")

        if not rule_id:
            errors.append(f"HB013: Exception for {script} missing rule_id")

        if not ticket:
            errors.append(f"HB013: Exception for {script} missing ticket")

        if expires_on:
            try:
                exp_date = datetime.date.fromisoformat(str(expires_on))
                if exp_date < today:
                    errors.append(f"HB013: Exception for {script} expired on {expires_on}")
            except Exception:
                errors.append(f"HB013: Exception for {script} has invalid expires_on: {expires_on}")

    return errors


# ----------------------------
# Public API
# ----------------------------
def load_policy(repo_root: Path) -> Dict[str, Any]:
    """Load and validate policy SSOT."""
    ssot_path = repo_root / SSOT_YAML_RELPATH
    schema_path = repo_root / "scripts" / "_policy" / "scripts.policy.schema.json"

    if not ssot_path.exists():
        raise FileNotFoundError(f"SSOT not found: {ssot_path}")

    policy = load_yaml(ssot_path)

    # Schema validation (if schema exists)
    if schema_path.exists():
        schema = load_json(schema_path)
        schema_errors = validate_schema(policy, schema)
        if schema_errors:
            raise ValueError(f"Schema validation failed:\n" + "\n".join(schema_errors))

    # Semantic validation
    semantic_errors = semantic_validate(policy)
    if semantic_errors:
        raise ValueError(f"Semantic validation failed:\n" + "\n".join(semantic_errors))

    return policy


def render_derived_md(policy: Dict[str, Any]) -> str:
    """Render DERIVED Markdown from policy (deterministic)."""
    return render_md(policy)


def validate_policy_compliance(repo_root: Path) -> Tuple[int, List[str]]:
    """
    Validate all scripts against policy.
    
    Returns: (exit_code, messages)
      - exit_code: 0 OK, 2 VIOLATIONS, 3 HARNESS_ERROR
      - messages: list of violation/error strings
    """
    try:
        policy = load_policy(repo_root)
        heuristics_path = repo_root / HEURISTICS_YAML_RELPATH
        heuristics = load_heuristics(heuristics_path)

        # Validate exceptions
        exceptions = load_exceptions(policy)
        exc_errors = validate_exceptions(exceptions)
        if exc_errors:
            return 2, exc_errors

        # Validate scripts
        violations = validate_scripts(repo_root, policy, heuristics)

        # Filter out exceptions
        filtered = []
        for rule_id, path, msg in violations:
            exc = exceptions.get(path, {})
            if exc.get("rule_id") == rule_id:
                continue  # Exception applies
            filtered.append(f"{rule_id}|{path}|{msg}")

        if filtered:
            return 2, filtered

        return 0, ["OK: All scripts comply with policy"]

    except FileNotFoundError as e:
        return 3, [f"HARNESS_ERROR: {e}"]
    except ValueError as e:
        return 2, [f"POLICY_INVALID: {e}"]
    except Exception as e:
        return 3, [f"HARNESS_ERROR: {type(e).__name__}: {e}"]


if __name__ == "__main__":
    # Simple CLI for testing
    repo = Path(os.getcwd()).resolve()
    exit_code, messages = validate_policy_compliance(repo)
    for msg in messages:
        print(msg)
    sys.exit(exit_code)
