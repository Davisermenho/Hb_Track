# AI Agent Documentation Index (MOVED)

**This file has been consolidated into the canonical documentation.**

---

## ⚠️ IMPORTANT: This file is now a stub redirect

The content previously in this file has been unified with the canonical documentation to eliminate duplication and establish a single source of truth for navigation.

**New canonical location:** [`docs/_canon/00_START_HERE.md`](../_canon/00_START_HERE.md)

---

## Why This Change?

**Governance Audit Finding:** [GOVERNANCE_AUDIT_REPORT.md](../_canon/_agent/GOVERNANCE_AUDIT_REPORT.md) identified critical issues:
- **85% content overlap** between `_INDEX.md` and `00_START_HERE.md`
- **3 competing indices** created ambiguity of authority
- **High risk of drift** due to duplicated maintenance

**Resolution (ADR-NNN):** Unify all navigation content into `docs/_canon/00_START_HERE.md` as the single authoritative entry point.

---

## Document Hierarchy (Precedence Order)

In case of conflict between documents, the following hierarchy applies:

```
LEVEL 0: AI Governance Formal
  └─ docs/_canon/GOVERNANCE_MODEL.md

LEVEL 1: Canonical Documentation (AUTHORITY)
  └─ docs/_canon/00_START_HERE.md ← **START HERE**
  └─ docs/_canon/*.md (workflows, pipelines, approved commands, etc)

LEVEL 2: Operational Documentation
  └─ docs/_ai/*.md (prompts, protocols, guardrails)
  └─ docs/_ai/_*/*.md (subdirectories: _context, _specs, _maps, etc)

LEVEL 3: Generated Artifacts
  └─ docs/_generated/*.* (schema.sql, openapi.json, parity_report.json)
```

**Rule:** Lower levels CANNOT override higher levels.

---

## Quick Navigation (Essential Links)

For agents starting work on HB Track:

1. **Start Here:** [00_START_HERE.md](../_canon/00_START_HERE.md) — Single entry point
2. **SSOT & Authority:** [01_AUTHORITY_SSOT.md](../_canon/01_AUTHORITY_SSOT.md) — Precedence rules
3. **Models Pipeline:** [05_MODELS_PIPELINE.md](../_canon/05_MODELS_PIPELINE.md) — Validation workflows
4. **Approved Commands:** [08_APPROVED_COMMANDS.md](../_canon/08_APPROVED_COMMANDS.md) — Command whitelist
5. **Troubleshooting:** [09_TROUBLESHOOTING_GUARD_PARITY.md](../_canon/09_TROUBLESHOOTING_GUARD_PARITY.md) — Exit code diagnosis

---

## Backward Compatibility

**Deprecation Timeline:**
- **v2.0.0 (2026-02-13)**: Stub created; canonical location operational
- **v2.1.0 (TBD)**: Warning added to CI/CD if `_INDEX.md` is referenced
- **v2.2.0 (TBD)**: Stub may be removed (pending validation of no external references)

**If you have links pointing here:** Please update to `docs/_canon/00_START_HERE.md`

---

## For AI Agents: Mandatory Action

**Before proceeding with any task:**

1. ✅ Acknowledge you have read [`docs/_canon/00_START_HERE.md`](../_canon/00_START_HERE.md)
2. ✅ Confirm understanding of LEVEL 0-3 hierarchy (above)
3. ✅ Verify your working directory (`Get-Location` or `pwd`)
4. ✅ Check repo is clean (`git status --porcelain` should be empty)

**Then:** Follow the "Quick Start Routing" in the canonical documentation.

---

**Effective Date:** 2026-02-13  
**ADR Reference:** ADR-NNN (pending creation)  
**Related Audit:** [GOVERNANCE_AUDIT_REPORT.md](../_canon/_agent/GOVERNANCE_AUDIT_REPORT.md) (Section 7, R1)

**END OF STUB**
