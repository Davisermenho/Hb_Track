#!/usr/bin/env python3
"""
HB Track Self-Healing Governance

Detects drift and generates corrective patches automatically.
Integrates with agent_drift_detector.py for detection and
prompt_sanitizer.py for language remediation.

Exit codes:
0 = No drift / all healed
1 = Patches suggested (dry-run)
2 = Unresolvable issues remain

Usage:
    python self_healing_governance.py              # dry-run (default)
    python self_healing_governance.py --apply      # apply patches
    python self_healing_governance.py --report     # JSON report only

Version: 1.0.0
Last Updated: 2026-02-13
"""

from pathlib import Path
import argparse
import difflib
import json
import re
import sys
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import REPO_ROOT

# Import sibling modules
from agent_drift_detector import (
    scan_file, DriftIssue, CONVERSATIONAL, HEDGING, PROMOTIONAL
)
from prompt_sanitizer import sanitize


# Section templates for missing sections (from ARCH_REQUEST_GENERATION_PROTOCOL)
ARCH_REQUEST_TEMPLATES = {
    "## 1. CONTEXTO / PROBLEMA": "\n\n> [TODO: Descrever o contexto e problema que motiva esta ARCH_REQUEST]\n",
    "## 2. OBJETIVOS (MUST)": "\n\n- [ ] [TODO: Definir objetivos usando RFC 2119 keywords (MUST/SHALL/REQUIRED)]\n",
    "## 3. SSOT & AUTORIDADE": "\n\n> **Fonte:** [TODO: Referenciar schema.sql, openapi.json ou outro artefato canônico]\n",
    "## 4. DELTA ESTRUTURAL": "\n\n> [TODO: Descrever mudanças estruturais esperadas]\n",
    "## 5. PROTOCOLO DO EXECUTOR (MANDATÓRIO)": "\n\n> [TODO: Instruções para o executor]\n",
    "## 6. ESPECIFICAÇÃO DO event.json": "\n\n```json\n{\"TODO\": \"Definir event.json\"}\n```\n",
    "## 7. GATES DE ACEITAÇÃO": "\n\n- [ ] [TODO: Definir critérios de aceitação verificáveis]\n",
}

EXEC_TASK_TEMPLATES = {
    "OBJETIVO EXECUTÁVEL": "\n\n> [TODO: Objetivo executável claro]\n",
    "PRÉ-REQUISITOS": "\n\n- [ ] [TODO: Listar pré-requisitos]\n",
    "FASES DE EXECUÇÃO": "\n\n### Fase 1\n- [ ] [TODO: Definir fases]\n",
}


class HealAction:
    """Represents a corrective action for a drift issue."""

    def __init__(self, file: Path, issue: DriftIssue, action: str,
                 original: str, patched: Optional[str] = None):
        self.file = file
        self.issue = issue
        self.action = action  # "patch", "report_only"
        self.original = original
        self.patched = patched  # None if report_only

    def diff(self) -> str:
        """Generate unified diff between original and patched content."""
        if not self.patched or self.original == self.patched:
            return ""
        rel = str(self.file.relative_to(REPO_ROOT))
        return "\n".join(difflib.unified_diff(
            self.original.splitlines(),
            self.patched.splitlines(),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm=""
        ))


def heal_language_drift(file: Path, content: str, issue: DriftIssue) -> HealAction:
    """Heal language drift by sanitizing conversational/hedging/promotional text."""
    patched = content

    if "Conversational" in issue.message or "conversational" in issue.message:
        patched = CONVERSATIONAL.sub("", patched)

    if "Hedging" in issue.message or "hedging" in issue.message:
        # Replace hedging with normative equivalents
        replacements = {
            "deveria": "MUST",
            "should consider": "SHALL",
            "pode ser que": "may",
            "might": "may",
            "é possível": "can",
            "it's possible": "can",
            "provavelmente": "is expected to",
            "probably": "is expected to",
        }
        for old, new in replacements.items():
            patched = re.sub(rf"\b{re.escape(old)}\b", new, patched, flags=re.IGNORECASE)

    if "Promotional" in issue.message or "promotional" in issue.message:
        replacements = {
            "melhor solução": "canonical solution",
            "best solution": "canonical solution",
            "ideal": "deterministic",
            "perfeito": "compliant",
            "perfect": "compliant",
        }
        for old, new in replacements.items():
            patched = re.sub(rf"\b{re.escape(old)}\b", new, patched, flags=re.IGNORECASE)

    # Clean up double spaces
    patched = re.sub(r"  +", " ", patched)

    if patched != content:
        return HealAction(file, issue, "patch", content, patched)
    return HealAction(file, issue, "report_only", content)


def heal_structural_drift(file: Path, content: str, issue: DriftIssue) -> HealAction:
    """Heal structural drift where possible."""

    # JSON in Markdown — cannot auto-fix safely, report only
    if "JSON detected" in issue.message:
        return HealAction(file, issue, "report_only", content)

    # Mixed layers — cannot split automatically, report only
    if "Mixed layers" in issue.message:
        return HealAction(file, issue, "report_only", content)

    return HealAction(file, issue, "report_only", content)


def heal_missing_sections(file: Path, content: str) -> Optional[HealAction]:
    """Add missing sections to ARCH_REQUEST files."""
    if "# ARCH_REQUEST" not in content:
        return None

    patched = content
    added = []

    for section, template in ARCH_REQUEST_TEMPLATES.items():
        if section not in content:
            patched += f"\n{section}{template}"
            added.append(section)

    if added:
        dummy_issue = DriftIssue(
            file, "structural", "BLOCKER",
            f"Missing sections: {', '.join(added)}"
        )
        return HealAction(file, dummy_issue, "patch", content, patched)
    return None


def heal_protocol_drift(file: Path, content: str, issue: DriftIssue) -> HealAction:
    """Protocol drift requires human review — always report_only."""
    return HealAction(file, issue, "report_only", content)


def process_file(file: Path) -> List[HealAction]:
    """Detect drift in a file and generate heal actions."""
    try:
        content = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    issues = scan_file(file)
    actions = []

    for issue in issues:
        if issue.type == "language":
            actions.append(heal_language_drift(file, content, issue))
        elif issue.type == "structural":
            actions.append(heal_structural_drift(file, content, issue))
        elif issue.type == "protocol":
            actions.append(heal_protocol_drift(file, content, issue))

    # Check for missing sections (independent of drift detector)
    missing_action = heal_missing_sections(file, content)
    if missing_action:
        actions.append(missing_action)

    return actions


def apply_patches(actions: List[HealAction]) -> int:
    """Apply patchable actions to files."""
    applied = 0
    for action in actions:
        if action.action == "patch" and action.patched:
            action.file.write_text(action.patched, encoding="utf-8")
            applied += 1
            print(f"[HEALED] {action.file.relative_to(REPO_ROOT)}")
    return applied


def generate_report(actions: List[HealAction]) -> Dict:
    """Generate JSON report of all actions."""
    report = {
        "total_issues": len(actions),
        "patchable": sum(1 for a in actions if a.action == "patch"),
        "report_only": sum(1 for a in actions if a.action == "report_only"),
        "actions": [],
    }
    for action in actions:
        entry = {
            "file": str(action.file.relative_to(REPO_ROOT)),
            "type": action.issue.type,
            "severity": action.issue.severity,
            "message": action.issue.message,
            "action": action.action,
        }
        if action.action == "patch":
            entry["diff_preview"] = action.diff()[:500]
        report["actions"].append(entry)

    return report


def main():
    parser = argparse.ArgumentParser(description="HB Track Self-Healing Governance")
    parser.add_argument("--apply", action="store_true", help="Apply patches (default: dry-run)")
    parser.add_argument("--report", action="store_true", help="Output JSON report only")
    args = parser.parse_args()

    print("=" * 60)
    print("HB Track Self-Healing Governance v1.0.0")
    print("=" * 60)

    scan_paths = [
        REPO_ROOT / "docs/_canon",
        REPO_ROOT / "docs/execution_tasks",
        REPO_ROOT / "docs/execution_tasks/artifacts",
        REPO_ROOT / "docs/ADR",
    ]

    all_actions: List[HealAction] = []
    scanned = 0

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue
        for md_file in scan_path.rglob("*.md"):
            if "TEMPLATE" in md_file.name or "_INDEX" in md_file.name:
                continue
            scanned += 1
            all_actions.extend(process_file(md_file))

    patchable = [a for a in all_actions if a.action == "patch"]
    report_only = [a for a in all_actions if a.action == "report_only"]

    if args.report:
        print(json.dumps(generate_report(all_actions), indent=2, ensure_ascii=False))
        sys.exit(0)

    # Show diffs for patchable issues
    if patchable:
        print(f"\n[PATCHABLE] {len(patchable)} issues can be auto-healed:")
        for action in patchable:
            print(f"\n--- {action.file.relative_to(REPO_ROOT)} ---")
            print(f"Issue: {action.issue.message}")
            diff = action.diff()
            if diff:
                # Show first 20 lines of diff
                lines = diff.splitlines()
                for line in lines[:20]:
                    print(line)
                if len(lines) > 20:
                    print(f"  ... ({len(lines) - 20} more lines)")

    if report_only:
        print(f"\n[MANUAL] {len(report_only)} issues require human review:")
        for action in report_only:
            rel = action.file.relative_to(REPO_ROOT)
            print(f"  [{action.issue.severity}] {rel}: {action.issue.message}")

    # Apply if requested
    if args.apply and patchable:
        print(f"\nApplying {len(patchable)} patches...")
        applied = apply_patches(patchable)
        print(f"[DONE] {applied} files patched.")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Files scanned: {scanned}")
    print(f"Patchable:     {len(patchable)}")
    print(f"Manual review: {len(report_only)}")
    print("=" * 60)

    if not all_actions:
        print("[OK] No drift detected. Governance clean.")
        sys.exit(0)
    elif args.apply:
        if report_only:
            sys.exit(2)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
