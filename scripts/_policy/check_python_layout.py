#!/usr/bin/env python3
"""
HB Track — check_python_layout.py (R12: Repo-Wide Layout Validator)

Validates that .py files only exist in approved roots (repo-wide).
Deterministic output (sorted), deterministic exit codes (0/2/3).

Exit codes:
  0 = PASS (or REPORT-ONLY with violations)
  2 = FAIL (violations found in enforce mode)
  3 = HARNESS ERROR (git/config/policy issue)

Version: 1.1.0 (SSOT-enabled)
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import yaml  # PyYAML
except Exception as e:
    print(f"R12-E_DEP_MISSING | scripts/_policy/check_python_layout.py | Missing PyYAML: {e}", file=sys.stderr)
    sys.exit(3)

# Exit codes
EXIT_OK = 0
EXIT_VIOLATION = 2
EXIT_ERROR = 3

DEFAULT_POLICY_REL = "scripts/_policy/python_layout.policy.yaml"


def norm_path(p: str) -> str:
    return p.replace("\\", "/")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _ensure_root_slash(s: str) -> str:
    s = norm_path(s).strip()
    if not s.endswith("/"):
        s += "/"
    return s


def _stable_relpath(repo_root: Path, p: Path) -> str:
    try:
        rp = p.resolve().relative_to(repo_root.resolve())
        return norm_path(str(rp))
    except Exception:
        return norm_path(str(p))


def load_policy(repo_root: Path, policy_path: Path) -> dict:
    if not policy_path.exists():
        raise ValueError(f"policy not found: {policy_path}")

    data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("policy YAML must be a mapping")

    if "policy" not in data or not isinstance(data["policy"], dict):
        raise ValueError("missing 'policy' mapping")

    pol = data["policy"]
    mode = pol.get("mode", "enforce")
    if mode not in ("report_only", "enforce"):
        raise ValueError("policy.mode must be one of: report_only, enforce")

    allowed_roots = pol.get("allowed_roots", [])
    forbidden_prefixes = pol.get("forbidden_prefixes", [])
    ignore_globs = pol.get("ignore_globs", [])

    if not isinstance(allowed_roots, list) or not all(isinstance(x, str) for x in allowed_roots):
        raise ValueError("policy.allowed_roots must be list[str]")
    if not isinstance(forbidden_prefixes, list) or not all(isinstance(x, str) for x in forbidden_prefixes):
        raise ValueError("policy.forbidden_prefixes must be list[str]")
    if not isinstance(ignore_globs, list) or not all(isinstance(x, str) for x in ignore_globs):
        raise ValueError("policy.ignore_globs must be list[str]")

    allowed_roots_n = sorted({_ensure_root_slash(x) for x in allowed_roots})
    forbidden_prefixes_n = sorted({norm_path(x).strip() for x in forbidden_prefixes if norm_path(x).strip()})
    ignore_globs_n = sorted({norm_path(x).strip() for x in ignore_globs if norm_path(x).strip()})

    # Stable fingerprint for audit/debug (does not replace POLICY_SHA256)
    fp_text = (
        "MODE=" + mode + "\n"
        + "ALLOWED_ROOTS=\n" + "\n".join(allowed_roots_n) + "\n"
        + "FORBIDDEN_PREFIXES=\n" + "\n".join(forbidden_prefixes_n) + "\n"
        + "IGNORE_GLOBS=\n" + "\n".join(ignore_globs_n) + "\n"
    ).encode("utf-8")
    roots_sha = sha256_bytes(fp_text)

    return {
        "mode": mode,
        "allowed_roots": allowed_roots_n,
        "forbidden_prefixes": forbidden_prefixes_n,
        "ignore_globs": ignore_globs_n,
        "policy_sha256": sha256_file(policy_path),
        "roots_sha256": roots_sha,
        "policy_path_display": _stable_relpath(repo_root, policy_path),
    }


def git_ls_files_py(repo_root: Path) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.py"],
            cwd=repo_root,
            capture_output=True,
            text=False,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git ls-files failed (exit {result.returncode})")

        paths_raw = result.stdout.decode("utf-8", errors="replace").split("\0")
        paths = [norm_path(p.strip()) for p in paths_raw if p.strip()]
        return paths
    except Exception as e:
        raise RuntimeError(f"Failed to enumerate .py files: {e}")


def is_ignored(path: str, ignore_globs: List[str]) -> bool:
    for pat in ignore_globs:
        # fnmatch works with "/" because we normalized
        if fnmatch.fnmatch(path, pat):
            return True
    return False


def validate_python_layout(repo_root: Path, policy: dict) -> Tuple[int, List[str], int]:
    py_files = git_ls_files_py(repo_root)

    violations: List[str] = []
    scanned = 0

    for path in py_files:
        if is_ignored(path, policy["ignore_globs"]):
            continue

        scanned += 1

        if any(path.startswith(fp) for fp in policy["forbidden_prefixes"]):
            violations.append(f"LAYOUT-E_FORBIDDEN_PATH | {path} | In forbidden prefix")
            continue

        is_allowed = any(path.startswith(root) for root in policy["allowed_roots"])
        if not is_allowed:
            violations.append(f"LAYOUT-E_PYTHON_OUTSIDE_ROOT | {path} | Not in allowed roots")

    violations.sort()
    mode = policy["mode"]

    if violations and mode == "enforce":
        return EXIT_VIOLATION, violations, scanned
    return EXIT_OK, violations, scanned


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(
        "--policy",
        default=DEFAULT_POLICY_REL,
        help="Path to python layout policy YAML (relative to repo root or absolute).",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = (repo_root / policy_path).resolve()

    print("[check_python_layout] Validating Python file layout...")

    try:
        pol = load_policy(repo_root, policy_path)
    except Exception as e:
        print(f"R12-E_POLICY_INVALID | {norm_path(str(args.policy))} | {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    # Deterministic audit lines (no absolute repo root)
    print(f"POLICY_PATH={pol['policy_path_display']}")
    print(f"POLICY_SHA256={pol['policy_sha256']}")
    print(f"ROOTS_SHA256={pol['roots_sha256']}")
    print(f"MODE={pol['mode']}")
    print(f"IGNORE_GLOBS_COUNT={len(pol['ignore_globs'])}")
    print(f"ALLOWED_ROOTS_COUNT={len(pol['allowed_roots'])}")

    try:
        exit_code, violations, scanned = validate_python_layout(repo_root, pol)
    except Exception as e:
        print(f"R12-E_GIT_FAILED | git ls-files -z -- *.py | {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    print(f"SCANNED_COUNT={scanned}")
    print(f"VIOLATIONS_COUNT={len(violations)}")

    if violations:
        if pol["mode"] == "report_only":
            print(f"[REPORT] {len(violations)} violation(s) found (report_only):\n")
        else:
            print(f"[FAIL] {len(violations)} violation(s) found:\n")
        for v in violations:
            print(v)

        # Print roots deterministically for actionability
        print("\nAllowed roots:")
        for root in pol["allowed_roots"]:
            print(f"  - {root}")

    else:
        print("[OK] All .py files in allowed roots")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
