#!/usr/bin/env python3
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SIDE_EFFECTS: FS_READ
# HB_SCRIPT_SCOPE: guard
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: python scripts/checks/db/agent_guard.py
# HB_SCRIPT_OUTPUTS: baseline.json, exit_code

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Use env var HB_DOCS_GENERATED_DIR if set, else default to _generated
GENERATED_DIR_NAME = os.getenv("HB_DOCS_GENERATED_DIR", "_generated")
INTERNAL_EXCLUDES = [".hb_guard", ".git", f"docs/{GENERATED_DIR_NAME}"]
EXCLUDED_DIRS = {".git", ".hb_guard", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc"}


def merge_excludes(exclude_patterns: List[str]) -> List[str]:
    # preserve order, remove duplicates
    out: List[str] = []
    for x in INTERNAL_EXCLUDES + exclude_patterns:
        x = (x or "").strip()
        if not x:
            continue
        if x not in out:
            out.append(x)
    return out


@dataclass(frozen=True)
class FileSig:
    sha256: str
    size: int


def sha256_file(path: Path) -> FileSig:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return FileSig(sha256=h.hexdigest(), size=size)


def norm_rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root)).replace("/", "\\")


def parse_csv_patterns(s: str) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def is_excluded(rel: str, exclude_patterns: List[str]) -> bool:
    rel_n = rel.replace("/", "\\")
    for pat in exclude_patterns:
        pat_n = pat.replace("/", "\\")
        if fnmatch.fnmatch(rel_n, pat_n) or rel_n.startswith(pat_n.rstrip("\\") + "\\"):
            return True
    return False


def _is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def walk_files(root: Path, exclude_patterns: List[str]) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)

        # prune excluded directories to avoid descending into them
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_excluded(dir_path / d)
            and not is_excluded(norm_rel(root, dir_path / d), exclude_patterns)
        ]

        for filename in filenames:
            p = dir_path / filename
            if _is_excluded(p):
                continue
            rel = norm_rel(root, p)
            if is_excluded(rel, exclude_patterns):
                continue
            files.append(p)
    return files


def build_manifest(root: Path, exclude_patterns: List[str]) -> Dict[str, Dict[str, object]]:
    manifest: Dict[str, Dict[str, object]] = {}
    for p in walk_files(root, exclude_patterns):
        rel = norm_rel(root, p)
        sig = sha256_file(p)
        manifest[rel] = {"sha256": sig.sha256, "size": sig.size}
    return manifest


def load_manifest(path: Path) -> Dict[str, Dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("baseline manifest must be a JSON object")
    return data  # type: ignore[return-value]


def match_any(rel: str, patterns: List[str]) -> bool:
    rel_n = rel.replace("/", "\\")
    return any(fnmatch.fnmatch(rel_n, p.replace("/", "\\")) for p in patterns)


def assert_skip_model_only_empty(envpy: Path) -> None:
    txt = envpy.read_text(encoding="utf-8", errors="replace")
    # Hard rule: SKIP_MODEL_ONLY_TABLES must remain exactly an empty set() assignment.
    # This prevents masking "model-only" tables during SCAN_ONLY.
    if "SKIP_MODEL_ONLY_TABLES" not in txt:
        raise RuntimeError(f"{envpy}: SKIP_MODEL_ONLY_TABLES not found (unexpected)")
    # Accept either `set()` or `set( )` spacing variants, but must be empty.
    import re
    m = re.search(r"SKIP_MODEL_ONLY_TABLES\s*=\s*set\s*\(\s*\)\s*", txt)
    if not m:
        raise RuntimeError(
            f"{envpy}: SKIP_MODEL_ONLY_TABLES is not an empty set() assignment (masking risk)"
        )


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    exclude = merge_excludes(parse_csv_patterns(args.exclude))
    manifest = build_manifest(root, exclude)

    payload = {
        "root": str(root),
        "exclude": exclude,
        "files": manifest,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[OK] baseline written: {out}")
    print(f"[OK] file_count={len(manifest)}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    baseline_path = Path(args.baseline).resolve()

    baseline = load_manifest(baseline_path)
    base_root = baseline.get("root")
    base_files = baseline.get("files")
    exclude = baseline.get("exclude", [])
    if not isinstance(base_files, dict):
        raise ValueError("baseline missing 'files' map")

    exclude_patterns = merge_excludes(list(exclude) if isinstance(exclude, list) else [])
    current = build_manifest(root, exclude_patterns)
    # If baseline file is inside root, ignore it to avoid self-triggering.
    try:
        baseline_rel = norm_rel(root, baseline_path)
        current.pop(baseline_rel, None)
    except Exception:
        pass

    allow = parse_csv_patterns(args.allow)
    forbid_new = args.forbid_new
    forbid_delete = args.forbid_delete

    base_set = set(base_files.keys())
    cur_set = set(current.keys())

    added = sorted(cur_set - base_set)
    deleted = sorted(base_set - cur_set)

    modified: List[str] = []
    for rel in sorted(cur_set & base_set):
        b = base_files[rel]
        c = current[rel]
        if (b.get("sha256"), b.get("size")) != (c.get("sha256"), c.get("size")):
            modified.append(rel)

    violations: List[str] = []

    def record_change(kind: str, rel: str) -> None:
        if allow and match_any(rel, allow):
            return
        violations.append(f"{kind}: {rel}")

    if forbid_new:
        for rel in added:
            record_change("NEW", rel)
    else:
        for rel in added:
            if allow and not match_any(rel, allow):
                violations.append(f"NEW (not allowed by allowlist): {rel}")

    if forbid_delete:
        for rel in deleted:
            record_change("DELETED", rel)
    else:
        for rel in deleted:
            if allow and not match_any(rel, allow):
                violations.append(f"DELETED (not allowed by allowlist): {rel}")

    for rel in modified:
        record_change("MODIFIED", rel)

    if args.assert_skip_model_only_empty:
        assert_skip_model_only_empty(Path(args.assert_skip_model_only_empty).resolve())

    if violations:
        print("[FAIL] guard violations:")
        for v in violations[:200]:
            print("  -", v)
        if len(violations) > 200:
            print(f"  ... ({len(violations) - 200} more)")
        return 3

    print("[OK] guard check passed")
    if base_root and str(root) != str(base_root):
        print(f"[WARN] baseline root differs: baseline={base_root} current={root}")
    print(f"[OK] added={len(added)} deleted={len(deleted)} modified={len(modified)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="agent_guard")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("snapshot", help="Create baseline manifest (sha256/size) for repo")
    sp.add_argument("--root", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--exclude", default="")  # CSV patterns/prefixes
    sp.set_defaults(func=cmd_snapshot)

    cp = sub.add_parser("check", help="Check repo against baseline manifest")
    cp.add_argument("--root", required=True)
    cp.add_argument("--baseline", required=True)
    cp.add_argument("--allow", default="")  # CSV glob patterns (relative paths)
    cp.add_argument("--forbid-new", action="store_true")
    cp.add_argument("--forbid-delete", action="store_true")
    cp.add_argument("--assert-skip-model-only-empty", default="")
    cp.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    return int(args.func(args))  # type: ignore[misc]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("[ERROR]", repr(e))
        raise