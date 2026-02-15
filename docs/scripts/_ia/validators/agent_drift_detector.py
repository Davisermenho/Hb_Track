#!/usr/bin/env python3
"""
HB Track Agent Drift Detector

Detects governance drift in HB Track artifacts:
- JSON where Markdown expected
- Mixed layers (ARCH_REQUEST + EXEC_TASK in same file)
- Conversational tone (hedging words, opinions)
- Protocol violations (execution in architecture, etc.)

Rules loaded from: docs/_canon/_agent/AGENT_DRIFT_RULES.md

Exit codes:
0 = No drift detected
1 = Warnings (non-blocking)
2 = Blockers (must fix)

Version: 1.0.0
Last Updated: 2026-02-13
"""

from pathlib import Path
import re
import sys
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import REPO_ROOT

# Drift detection patterns (from AGENT_DRIFT_RULES.md)
JSON_START = re.compile(r"^\s*\{", re.MULTILINE)
JSON_CODE_BLOCK = re.compile(r"```(?:json|javascript|typescript)\s*\n.*?\n```", re.DOTALL)
CONVERSATIONAL = re.compile(
    r"\b(acho que|I think|podemos|we can|na minha opinião|in my opinion|"
    r"seria legal|it would be nice|talvez|maybe|recomendo|I recommend)\b",
    re.IGNORECASE
)
HEDGING = re.compile(
    r"\b(deveria|should consider|pode ser que|might|é possível|it'?s possible|"
    r"provavelmente|probably)\b",
    re.IGNORECASE
)
PROMOTIONAL = re.compile(
    r"\b(melhor solução|best solution|ideal|perfeito|perfect)\b",
    re.IGNORECASE
)
COMMANDS = re.compile(
    r"\b(powershell\.exe|python |bash |cmd\.exe|alembic |git commit|git push)\b",
    re.IGNORECASE
)

# Whitelist: files that are EXPECTED to contain JSON examples/documentation
JSON_ALLOWED_PATTERNS = [
    r"VALIDATION_MUST_REPORT.*\.md$",  # Validation reports document JSON output
    r"ARCH_REQUEST_IMPLEMENTED\.md$",  # Implementation docs may show JSON configs
    r"event\.json$",  # JSON files themselves
    r".*schema\.json$",  # JSON schema files
]

# Whitelist: files that are EXPECTED to contain command examples
COMMANDS_ALLOWED_PATTERNS = [
    r"ARCH_REQUEST_GENERATION_PROTOCOL\.md$",  # Teaches how to create arch requests (includes command examples)
    r".*_TUTORIAL\.md$",  # Tutorials show commands
    r".*_GUIDE\.md$",  # Guides show commands
    r"APPROVED_COMMANDS\.md$",  # Command catalog
    r"AGENT_DRIFT_RULES\.md$",  # Meta-documentation: teaches drift rules by example
    r"TROUBLESHOOTING.*\.md$",  # Troubleshooting guides show commands
    r"AR-.*-SCRIPTS-.*\.md$",  # AR-* for script refactoring naturally document commands
    r".*VALIDATION_MUST_REPORT.*\.md$",  # Validation reports document command execution
    r".*EXECUTION_PLAN.*\.md$",  # Execution plans document commands
    r"ARCH_REQUEST_IMPLEMENTED\.md$",  # Implementation documentation references commands
    r"AUTH-CONTEXT-SSOT-.*\.md$",  # Auth context docs reference git commands
]

# Whitelist: files that are EXPECTED to contain conversational/promotional language (teaching materials)
LANGUAGE_ALLOWED_PATTERNS = [
    r"AGENT_DRIFT_RULES\.md$",  # Meta-documentation: teaches about prohibited language by example
    r".*_TUTORIAL\.md$",  # Tutorials use friendlier language
]


class DriftIssue:
    """Represents a detected drift issue."""
    
    def __init__(self, file: Path, type: str, severity: str, message: str):
        self.file = file
        self.type = type  # "structural", "language", "protocol"
        self.severity = severity  # "WARNING", "BLOCKER"
        self.message = message
    
    def __str__(self):
        rel_path = self.file.relative_to(REPO_ROOT)
        return f"[{self.severity}] {self.type.upper()}: {rel_path} — {self.message}"


def detect_structural_drift(file: Path, content: str) -> List[DriftIssue]:
    """Detect structural drift (JSON, mixed layers, missing sections)."""
    issues = []
    
    # Check if file is whitelisted for JSON examples
    is_json_allowed = any(re.search(pattern, file.name) for pattern in JSON_ALLOWED_PATTERNS)
    
    # Check 1: JSON in Markdown (only if not whitelisted and not in code blocks)
    if file.suffix == ".md" and not is_json_allowed:
        # Remove code blocks before checking
        content_no_codeblocks = JSON_CODE_BLOCK.sub("", content)
        if JSON_START.search(content_no_codeblocks):
            issues.append(DriftIssue(
                file, "structural", "BLOCKER",
                "JSON detected in Markdown file (should be pure Markdown)"
            ))
    
    # Check 2: Mixed layers
    has_arch = "ARCH_REQUEST" in content and "# ARCH_REQUEST" in content
    has_exec = "EXEC_TASK" in content and "# EXEC_TASK" in content
    
    if has_arch and has_exec:
        issues.append(DriftIssue(
            file, "structural", "WARNING",
            "Mixed layers detected (ARCH_REQUEST + EXEC_TASK in same file)"
        ))
    
    return issues


def detect_language_drift(file: Path, content: str) -> List[DriftIssue]:
    """Detect language drift (conversational tone, hedging, promotional)."""
    issues = []
    
    # Check if file is whitelisted for friendly/teaching language
    is_language_allowed = any(re.search(pattern, file.name) for pattern in LANGUAGE_ALLOWED_PATTERNS)
    
    if is_language_allowed:
        return issues  # Skip all language checks for teaching materials
    
    # Check 1: Conversational tone
    conv_matches = CONVERSATIONAL.findall(content)
    if len(conv_matches) >= 3:
        issues.append(DriftIssue(
            file, "language", "BLOCKER",
            f"Conversational tone detected ({len(conv_matches)} instances: {set(conv_matches)})"
        ))
    elif conv_matches:
        issues.append(DriftIssue(
            file, "language", "WARNING",
            f"Conversational phrases detected: {set(conv_matches)}"
        ))
    
    # Check 2: Hedging language (in normative sections)
    if "## OBJETIVOS (MUST)" in content or "## GATES" in content:
        hedging_matches = HEDGING.findall(content)
        if hedging_matches:
            issues.append(DriftIssue(
                file, "language", "BLOCKER",
                f"Hedging language in normative section: {set(hedging_matches)}"
            ))
    
    # Check 3: Promotional language
    promo_matches = PROMOTIONAL.findall(content)
    if len(promo_matches) >= 4:
        issues.append(DriftIssue(
            file, "language", "BLOCKER",
            f"Promotional language detected ({len(promo_matches)} instances)"
        ))
    elif promo_matches:
        issues.append(DriftIssue(
            file, "language", "WARNING",
            f"Promotional language detected: {set(promo_matches)}"
        ))
    
    return issues


def detect_protocol_drift(file: Path, content: str) -> List[DriftIssue]:
    """Detect protocol drift (execution in arch, architecture in exec, etc.)."""
    issues = []
    
    # Check if file is whitelisted for command examples
    is_commands_allowed = any(re.search(pattern, file.name) for pattern in COMMANDS_ALLOWED_PATTERNS)
    
    # Check 1: Execution commands in ARCH_REQUEST (unless whitelisted)
    if "ARCH_REQUEST" in content and "# ARCH_REQUEST" in content and not is_commands_allowed:
        cmd_matches = COMMANDS.findall(content)
        if cmd_matches:
            issues.append(DriftIssue(
                file, "protocol", "BLOCKER",
                f"Executable commands in ARCH_REQUEST: {set(cmd_matches)}"
            ))
    
    # Check 2: Architecture redefinition in EXEC_TASK
    if "EXEC_TASK" in content and "# EXEC_TASK" in content:
        if "MUST add column" in content or "SHALL modify table" in content:
            issues.append(DriftIssue(
                file, "protocol", "BLOCKER",
                "Architectural requirements (MUST/SHALL) in EXEC_TASK (should be in ARCH_REQUEST)"
            ))
    
    # Check 3: Implementation in ADR
    if file.name.startswith("ADR-"):
        cmd_matches = COMMANDS.findall(content)
        # Allow code blocks if they're illustrative (not in ## Decisão with executable commands)
        if cmd_matches and "## Decisão" in content:
            issues.append(DriftIssue(
                file, "protocol", "WARNING",
                "Commands detected in ADR (should be in EXEC_TASK if executable)"
            ))
    
    return issues


def scan_file(file: Path) -> List[DriftIssue]:
    """Scan a single file for drift."""
    try:
        content = file.read_text(encoding="utf-8", errors="ignore")
        
        issues = []
        issues.extend(detect_structural_drift(file, content))
        issues.extend(detect_language_drift(file, content))
        issues.extend(detect_protocol_drift(file, content))
        
        return issues
    
    except Exception as e:
        print(f"[ERROR] Failed to scan {file}: {e}", file=sys.stderr)
        return []


def main():
    """Main drift detection orchestration."""
    print("=" * 60)
    print("HB Track Agent Drift Detector v1.0.0")
    print("=" * 60)
    
    # Scan relevant directories
    scan_paths = [
        REPO_ROOT / "docs/_canon",
        REPO_ROOT / "docs/execution_tasks",
        REPO_ROOT / "docs/execution_tasks/artifacts",
        REPO_ROOT / "docs/ADR",
    ]
    
    all_issues = []
    scanned_count = 0
    
    for scan_path in scan_paths:
        if not scan_path.exists():
            continue
        
        for md_file in scan_path.rglob("*.md"):
            # Skip templates and indexes
            if "TEMPLATE" in md_file.name or "_INDEX" in md_file.name:
                continue
            
            scanned_count += 1
            issues = scan_file(md_file)
            all_issues.extend(issues)
    
    # Report results
    warnings = [i for i in all_issues if i.severity == "WARNING"]
    blockers = [i for i in all_issues if i.severity == "BLOCKER"]
    
    if warnings:
        print("\n" + "=" * 60)
        print(f"WARNINGS ({len(warnings)}):")
        print("=" * 60)
        for issue in warnings:
            print(issue)
    
    if blockers:
        print("\n" + "=" * 60)
        print(f"BLOCKERS ({len(blockers)}):")
        print("=" * 60)
        for issue in blockers:
            print(issue)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Files scanned: {scanned_count}")
    print(f"Warnings: {len(warnings)}")
    print(f"Blockers: {len(blockers)}")
    print("=" * 60)
    
    # Exit codes
    if blockers:
        print("[FAIL] Drift blockers detected. Human review required.")
        sys.exit(2)
    elif warnings:
        print("[WARN] Drift warnings detected. Consider remediation.")
        sys.exit(1)
    else:
        print("[OK] No drift detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
