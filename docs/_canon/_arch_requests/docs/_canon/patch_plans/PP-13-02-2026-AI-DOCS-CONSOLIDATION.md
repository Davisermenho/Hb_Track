# PATCH_PLAN — AI DOCS CONSOLIDATION & FUNCTIONAL REORG (v1.0.0)
**PATCH_ID:** PP-YYYY-MM-DD-AI-DOCS-CONSOLIDATION  
**Mode:** READ-ONLY PLAN (to be executed by EXECUTOR)  
**Determinism Score:** 5/5  
**Priority:** HIGH  

## 0. SCOPE (MUST)
This PATCH_PLAN MUST:
- Reduce AI-governance-related docs count by ≥50% without losing enforceability.
- Reorganize files by function into a small set of folders.
- Preserve canonical authority rules (SSOT and precedence).
- Avoid breaking agent onboarding and existing links (via stubs + redirects).

This PATCH_PLAN MUST NOT:
- Change product behavior, DB schema, or application code.
- Introduce new governance concepts beyond consolidation/refactor.
- Require human “remembering paths”; navigation MUST be deterministic.

## 1. INPUTS / SSOT (MUST)
Authoritative inputs:
- `docs/_canon/00_START_HERE.md`
- `docs/_canon/AI_KERNEL.md`
- `docs/_canon/ARCH_REQUEST_DSL.md`
- `docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md`
- Current repo file tree snapshot (this plan references existing paths explicitly).

## 2. TARGET INFORMATION ARCHITECTURE (MUST)
After patch, AI docs MUST be organized under exactly these roots:

A) Repo Agent Instructions (IDE integration):
- `.github/instructions/`

B) Canonical Governance (human+agent):
- `docs/_canon/`

C) Operational Execution Evidence:
- `docs/execution_tasks/` (unchanged; only re-indexed)

D) Generated Artifacts (SSOT dumps/reports):
- `docs/_generated/` (unchanged)

E) Module/Product docs (not agent governance):
- `docs/00_product/`, `docs/02_modulos/`, `docs/ADR/`

No other “agent governance” folders are allowed after patch (MUST).

## 3. CONSOLIDATION RULES (MUST)
3.1 Canonical = small set:
- One entrypoint index (00_START_HERE or AI_GOVERNANCE_INDEX)
- One kernel (AI_KERNEL)
- One protocol bundle (AI_ARCH_EXEC_PROTOCOL + Language/Failsafe/DSL)
- One guardrails bundle (single folder + single index)

3.2 Everything else becomes:
- merged into canonical bundles OR
- converted to stub redirect OR
- archived (non-authoritative)

3.3 Stubs MUST:
- state DEPRECATED
- point to exact new canonical path + anchor
- include removal date policy

## 4. MOVE/MERGE MAP (DETERMINISTIC)
This section is the executable mapping. Each row MUST be unambiguous.

Table columns:
- ACTION: MOVE | MERGE | STUB | DELETE | KEEP
- FROM: current path
- TO: new path (if applicable)
- NOTES: constraints, anchors, or merge target section

| ACTION | FROM | TO | NOTES |
|---|---|---|---|
| KEEP | docs/_canon/AI_KERNEL.md | docs/_canon/AI_KERNEL.md | Canon |
| KEEP | docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md | docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md | Canon |
| ... | ... | ... | ... |

(Executor MUST fill this table completely before any destructive step.)

## 5. LINK MIGRATION (MUST)
- All moved docs MUST preserve inbound navigation via stubs.
- `docs/_canon/AI_GOVERNANCE_INDEX.md` MUST be updated (or generated) to reflect new structure.
- `.github/instructions/00_general.instructions.md` MUST reference only the new canonical roots.

## 6. ENFORCEMENT (MUST)
- CI MUST fail if new “agent governance” files are added outside allowed roots.
- Lint MUST validate:
  - ARCH_REQUEST DSL
  - logs compaction (if applicable)
  - governance index up-to-date (if generated)

## 7. GATES / ACCEPTANCE (MUST)
GATE-1: Tree compliance
- No agent governance docs remain under `docs/_ai/` (should be merged/moved/stubbed)
- No duplicate indices outside `docs/_canon/`

GATE-2: Navigation health
- All legacy entrypoints still resolve via stubs (no dead ends)
- `00_START_HERE.md` points to correct new locations

GATE-3: Count reduction
- Total count of “agent governance docs” reduced by ≥50% (define baseline count in artifacts)

GATE-4: CI enforcement
- New workflow (or existing) enforces no-sprawl rule

GATE-5: Idempotency
- Running index generator twice yields no diffs

## 8. EVIDENCE PACK (REQUIRED)
Executor MUST attach:
- Pre/post file counts (by root)
- Diff summary for moved/merged files
- `AI_GOVERNANCE_INDEX.md` diff (or generation proof)
- CI run link / logs

## 9. ROLLBACK (MUST)
- Rollback strategy = revert commit range for the patch.
- No partial state allowed: patch MUST be delivered as one PR or one linear series of commits with final squashed merge.
