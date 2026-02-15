#!/usr/bin/env python3
"""
HB Track Unified AI Governance Linter

Validates:
- ARCH_REQUEST structure (delegates to lint_arch_request.py)
- EXEC_TASK structure (light validation)
- ADR structure (basic checks)
- AI_KERNEL presence
- Protocol references
- Canon folder integrity

Exit codes:
0 = OK
2 = Structural violation
3 = Protocol violation
4 = Missing canon files

Version: 1.0.0
Last Updated: 2026-02-13
"""

from pathlib import Path
import re
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.paths import REPO_ROOT, CANON

REQUIRED_CANON = [
    "AI_KERNEL.md",
    "ARCH_REQUEST_GENERATION_PROTOCOL.md",
    "EXEC_TASK_GENERATION_PROTOCOL.md",
    "ADR_GENERATION_PROTOCOL.md",
    "_agent/AGENT_ROLE_MATRIX.md",
    "_agent/AGENT_DRIFT_RULES.md",
]

ARCH_REQ_PATTERN = re.compile(r"#\s+ARCH_REQUEST\s+—", re.MULTILINE)
EXEC_TASK_HEADER_PATTERNS = [
    re.compile(r"^#\s+EXEC_TASK\s+—", re.MULTILINE),
    re.compile(r"^#\s+EXEC_TASK\s*:", re.MULTILINE),
    re.compile(r"^##\s+EXEC_TASK\s+—", re.MULTILINE),
    re.compile(r"^#\s+TASK\s*:", re.MULTILINE),
]
ADR_PATTERN = re.compile(r"#\s+ADR-\d+\s+—", re.MULTILINE)


def fail(msg: str, code: int):
    """Print error and exit with code."""
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str):
    """Print warning (non-fatal)."""
    print(f"[WARN] {msg}", file=sys.stderr)


def check_canon():
    """Validate presence of required canonical files."""
    print("[CHECK] Validating canonical files...")
    missing = []
    for f in REQUIRED_CANON:
        path = CANON / f
        if not path.exists():
            missing.append(f)
    
    if missing:
        fail(f"Missing canon files: {', '.join(missing)}", 4)
    
    print(f"[OK] All {len(REQUIRED_CANON)} required canon files present.")


def lint_arch_requests():
    """Validate ARCH_REQUEST files (delegate to existing linter)."""
    print("[CHECK] Validating ARCH_REQUEST files...")
    
    # Find lint_arch_request.py
    lint_script = Path(__file__).resolve().parent / "lint_arch_request.py"
    if not lint_script.exists():
        warn("lint_arch_request.py not found, skipping ARCH_REQUEST validation")
        return
    
    # Run existing linter
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(lint_script),
                "--glob",
                "docs/_canon/_arch_requests/*.md",
                "--profile",
                "compat",
                "--skip-non-arch",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            fail(f"ARCH_REQUEST validation failed (exit {result.returncode})", result.returncode)
        
        print("[OK] ARCH_REQUEST files compliant.")
    
    except subprocess.TimeoutExpired:
        fail("ARCH_REQUEST linter timeout", 1)
    except Exception as e:
        warn(f"ARCH_REQUEST linter error: {e}")


def lint_exec_tasks():
    """Validate EXEC_TASK files (compat checks for current repo formats)."""
    print("[CHECK] Validating EXEC_TASK files...")
    
    exec_tasks = list(REPO_ROOT.rglob("EXEC_TASK*.md"))
    if not exec_tasks:
        print("[SKIP] No EXEC_TASK files found.")
        return
    
    violations = []
    
    for p in exec_tasks:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            
            # Check 1: Valid header (compat)
            if not any(pat.search(txt) for pat in EXEC_TASK_HEADER_PATTERNS):
                violations.append(f"{p.relative_to(REPO_ROOT)}: invalid EXEC_TASK header")
            
            # Check 2: No architecture redefinition (ARCH_REQUEST DSL forbidden)
            if "ARCH_REQUEST DSL" in txt:
                violations.append(f"{p.relative_to(REPO_ROOT)}: execution redefining architecture (ARCH_REQUEST content)")
            
            txt_up = txt.upper()
            has_objective = any(
                token in txt_up
                for token in [
                    "OBJETIVO EXECUTÁVEL",
                    "OBJETIVO DA FASE",
                    "## OBJETIVO",
                    "## EXEC_TASK",
                ]
            )
            has_prereq = any(
                token in txt_up
                for token in [
                    "PRÉ-REQUISITOS",
                    "PRE-REQUISITOS",
                    "DEPENDÊNCIAS",
                    "DEPENDENCIAS",
                    "AMBIENTE",
                    "CONTEXTO",
                ]
            )
            has_phases = any(
                token in txt_up
                for token in [
                    "FASES DE EXECUÇÃO",
                    "EXECUTION PLAN",
                    "## FASE 0",
                    "## FASE 1",
                ]
            ) or bool(re.search(r"^##\s+\d+\.\d+", txt, flags=re.MULTILINE))

            # Compat acceptance: require evidence of execution structure, not rigid headings.
            if not (has_objective or has_phases):
                violations.append(
                    f"{p.relative_to(REPO_ROOT)}: missing objective/execution structure (compat)"
                )

            if not (has_prereq or has_objective):
                violations.append(
                    f"{p.relative_to(REPO_ROOT)}: missing prerequisites/context structure (compat)"
                )
        
        except Exception as e:
            warn(f"Error reading {p}: {e}")
    
    if violations:
        for v in violations:
            print(f"[VIOLATION] {v}", file=sys.stderr)
        fail(f"EXEC_TASK validation failed ({len(violations)} violations)", 2)
    
    print(f"[OK] {len(exec_tasks)} EXEC_TASK files compliant.")


def lint_adrs():
    """Validate ADR files (basic structure checks)."""
    print("[CHECK] Validating ADR files...")
    
    adrs = list((REPO_ROOT / "docs/ADR").rglob("ADR-*.md"))
    if not adrs:
        print("[SKIP] No ADR files found.")
        return
    
    violations = []
    
    for p in adrs:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            
            # Check 1: Valid header
            if not ADR_PATTERN.search(txt):
                violations.append(f"{p.relative_to(REPO_ROOT)}: invalid ADR header (must be '# ADR-NNN —')")
            
            # Check 2: No execution commands
            forbidden_commands = ["powershell.exe", "python ", "bash ", "git commit", "alembic upgrade"]
            for cmd in forbidden_commands:
                if cmd in txt and "```" in txt:  # Commands in code blocks
                    # Allow code blocks in Decisão if they're illustrative (not executable)
                    if "## Decisão" in txt:
                        lines = txt.split("\n")
                        in_decision = False
                        in_code_block = False
                        for line in lines:
                            if "## Decisão" in line:
                                in_decision = True
                            elif line.startswith("##"):
                                in_decision = False
                            if in_decision and "```" in line:
                                in_code_block = not in_code_block
                            if in_decision and in_code_block and cmd in line:
                                violations.append(f"{p.relative_to(REPO_ROOT)}: executable command '{cmd}' in Decisão section")
                                break
            
            # Check 3: Required sections
            required = ["Contexto", "Decisão", "Consequências"]
            for section in required:
                if f"## {section}" not in txt and f"**{section}**" not in txt:
                    violations.append(f"{p.relative_to(REPO_ROOT)}: missing section '{section}'")
        
        except Exception as e:
            warn(f"Error reading {p}: {e}")
    
    if violations:
        for v in violations:
            print(f"[VIOLATION] {v}", file=sys.stderr)
        fail(f"ADR validation failed ({len(violations)} violations)", 2)
    
    print(f"[OK] {len(adrs)} ADR files compliant.")


def check_kernel_links():
    """Validate AI_KERNEL references to protocols."""
    print("[CHECK] Validating AI_KERNEL protocol references...")
    
    kernel = CANON / "AI_KERNEL.md"
    if not kernel.exists():
        fail("AI_KERNEL.md missing", 4)
    
    txt = kernel.read_text(encoding="utf-8")
    
    # Check for required references
    required_refs = [
        "AGENT_ROLE_MATRIX",
        "EXEC_TASK_GENERATION_PROTOCOL",
        "ADR_GENERATION_PROTOCOL"
    ]
    
    missing = [ref for ref in required_refs if ref not in txt]
    
    if missing:
        fail(f"AI_KERNEL missing protocol references: {', '.join(missing)}", 3)
    
    print("[OK] AI_KERNEL protocol references present.")


def main():
    """Main linter orchestration."""
    print("=" * 60)
    print("HB Track AI Governance Linter v1.0.0")
    print("=" * 60)
    
    try:
        check_canon()
        check_kernel_links()
        lint_arch_requests()
        lint_exec_tasks()
        lint_adrs()
        
        print("=" * 60)
        print("[SUCCESS] AI Governance validation complete.")
        print("All protocols compliant.")
        print("=" * 60)
        sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n[ABORT] Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
