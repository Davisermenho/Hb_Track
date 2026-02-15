<!--
DERIVED FILE — DO NOT EDIT BY HAND

This Markdown is derived from the SSOT policy:
- scripts/_policy/scripts.policy.yaml
Validated by:
- scripts/_policy/scripts.policy.schema.json

Edits MUST be applied to scripts.policy.yaml, then the generator MUST re-render this file.
-->

# HB Track — Scripts Classification (BCP14)

**Version:** 1.0.0  
**Date:** 2026-02-14  
**Status:** APPROVED  
**SSOT:** `scripts/_policy/scripts.policy.yaml`  
**Schema:** `scripts/_policy/scripts.policy.schema.json`  
**Derived:** `docs/_canon/_agent/SCRIPTS_classification.md` (this file)

## 1. Objective

This specification defines a **deterministic classification system** for ANY script created in this repository, using only:

1. Script intent (KIND)
2. Script side-effects (observable operations)
3. Fixed folder taxonomy + naming rules

A script that complies with this spec SHALL have exactly **one valid placement** (folder + sub-scope) and **one valid name pattern**.

## 2. Taxonomy (Top-Level Categories)

Deterministic precedence order (highest wins):

```
RESET > MIGRATE > FIXES > SEEDS > GENERATE > CHECKS > DIAGNOSTICS > OPS > TEMP > ARTIFACTS > RUN
```

## 3. Classification Dimensions

**KIND:** CHECK, DIAGNOSTIC, FIX, GENERATE, MIGRATE, OPS, RESET, SEED, RUNNER, TEMP, ARTIFACT

**SIDE_EFFECTS:** NONE, DB_READ, DB_WRITE, FS_READ, FS_WRITE, ENV_WRITE, NET, PROC_START_STOP, DESTRUCTIVE

**Extensions:** .py, .ps1, .sql

## 4. Required Headers

Every script MUST include these metadata fields:

- `HB_SCRIPT_KIND`
- `HB_SCRIPT_SCOPE`
- `HB_SCRIPT_SIDE_EFFECTS`
- `HB_SCRIPT_IDEMPOTENT`
- `HB_SCRIPT_ENTRYPOINT`
- `HB_SCRIPT_OUTPUTS`

Optional fields:

- `HB_SCRIPT_INPUTS`
- `HB_SCRIPT_RISK`
- `HB_SCRIPT_ROLLBACK`

## 5. Naming Convention

**Pattern:** `<prefix><scope>__<action>[_qualifier].<ext>`

**Prefix per category:**

| Category | Prefix |
| --- | --- |
| `checks/` | `check_` |
| `diagnostics/` | `diag_` |
| `fixes/` | `fix_` |
| `generate/` | `gen_` |
| `migrate/` | `mig_` |
| `ops/` | `ops_` |
| `reset/` | `reset_` |
| `run/` | `run_` |
| `seeds/` | `seed_` |
| `temp/` | `tmp_` |

## 6. Artifacts Policy

`scripts/artifacts/` is **OUTPUT-ONLY**, MUST be gitignored (except README), and MUST NOT be used as SSOT input.

## 7. Temp Policy

`scripts/temp/` is **quarantine**, MUST be gitignored, and MUST NOT be referenced by `scripts/run/` wrappers.

## 8. Determinism Acceptance Criteria

This system is deterministic if and only if:

1. Any new script's category is uniquely determined by constraints + precedence
2. Misplacements are mechanically detectable by gates
3. This Markdown matches the SSOT YAML (drift forbidden)
