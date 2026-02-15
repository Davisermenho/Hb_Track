#!/usr/bin/env python3
"""
validate-ssot-roots.py

Validate canonical root placement rules from PATHS_SSOT.yaml.

Exit codes:
  0 = OK
  1 = Execution/config error
  2 = SSOT root policy violation
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is required (pip install pyyaml).", file=sys.stderr)
    sys.exit(1)


def _to_posix(path: Path) -> str:
    return path.as_posix()


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid YAML structure: expected top-level mapping")
    return data


def _is_under_root(file_rel: str, root: str) -> bool:
    return file_rel == root or file_rel.startswith(root + "/")


def _collect_files(repo_root: Path, pattern: str) -> List[str]:
    matches = glob.glob(str(repo_root / pattern), recursive=True)
    rel: List[str] = []
    for m in matches:
        p = Path(m)
        if p.is_file():
            rel.append(_to_posix(p.resolve().relative_to(repo_root.resolve())))
    return sorted(set(rel))


def validate(config: Dict[str, Any], repo_root: Path, verbose: bool) -> List[str]:
    violations: List[str] = []

    roots = config.get("roots", {})
    if not isinstance(roots, dict):
        return ["Invalid config: 'roots' must be a mapping."]

    for root_id, root_cfg in roots.items():
        if not isinstance(root_cfg, dict) or "path" not in root_cfg:
            violations.append(f"roots.{root_id}: invalid definition (missing 'path').")
            continue
        root_path = str(root_cfg["path"]).strip()
        if not (repo_root / root_path).exists():
            violations.append(f"roots.{root_id}: path does not exist -> {root_path}")
        elif verbose:
            print(f"[OK] root exists: {root_id} -> {root_path}")

    for ssot_file in config.get("ssot_files", []):
        p = repo_root / str(ssot_file)
        if not p.exists():
            violations.append(f"Missing ssot_file: {ssot_file}")
        elif verbose:
            print(f"[OK] ssot_file exists: {ssot_file}")

    for rule in config.get("rules", []):
        rule_id = str(rule.get("id", "unknown"))
        include_globs = rule.get("include_globs", [])
        allowed_roots = [str(r).rstrip("/") for r in rule.get("allowed_roots", [])]
        require_matches = bool(rule.get("require_matches", False))

        if not include_globs or not allowed_roots:
            violations.append(f"rule {rule_id}: include_globs/allowed_roots must be non-empty.")
            continue

        matched: List[str] = []
        for pat in include_globs:
            matched.extend(_collect_files(repo_root, str(pat)))
        matched = sorted(set(matched))

        if require_matches and not matched:
            violations.append(f"rule {rule_id}: no files matched required patterns.")
            continue

        for f in matched:
            if not any(_is_under_root(f, root) for root in allowed_roots):
                violations.append(
                    f"rule {rule_id}: file outside allowed roots -> {f} | allowed={allowed_roots}"
                )

        if verbose:
            print(f"[INFO] rule {rule_id}: matched={len(matched)}")

    for forbidden_glob in config.get("forbidden_globs", []):
        hits = _collect_files(repo_root, str(forbidden_glob))
        for h in hits:
            violations.append(f"forbidden_glob violation: {h} matched '{forbidden_glob}'")
        if verbose:
            print(f"[INFO] forbidden_glob {forbidden_glob}: matches={len(hits)}")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="docs/_canon/PATHS_SSOT.yaml",
        help="Path to PATHS_SSOT.yaml",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root path",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    config_path = (repo_root / args.config).resolve()

    try:
        config = _load_yaml(config_path)
        violations = validate(config, repo_root=repo_root, verbose=args.verbose)
    except Exception as exc:
        print(f"[ERROR] validate-ssot-roots failed: {exc}", file=sys.stderr)
        return 1

    if violations:
        for v in violations:
            print(f"[VIOLATION] {v}", file=sys.stderr)
        print(f"[FAIL] SSOT root validation failed ({len(violations)} violations).", file=sys.stderr)
        return 2

    print("[OK] SSOT root validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
