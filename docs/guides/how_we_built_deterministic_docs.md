# How We Built Deterministic Documentation

**Status:** Guide  
**Last Updated:** 2026-02-16  
**Target Audience:** Developers, Architects, AI Agents

---

## Executive Summary

This document describes how HB Track achieved **deterministic documentation** — a state where documentation artifacts are cryptographically protected, regeneratable, and immune to silent drift or AI hallucination.

---

## The Problem

### Before: Documentation Chaos

In early HB Track development, documentation suffered from common problems:

| Problem | Symptom | Impact |
|---------|---------|--------|
| **Drift** | schema.sql ≠ OpenAPI spec | Developers trust wrong contracts |
| **Hallucination** | AI-generated docs that don't match code | False sense of security |
| **Manual edits** | Someone modifies generated files directly | Checksums don't match |
| **No single source** | Multiple "truths" for the same artifact | Confusion, bugs |

### The Breaking Point

When integrating the API with the frontend, we encountered a classic problem:

> "The schema says `user_id` but the OpenAPI says `id`. Which one is correct?"

The answer: **Neither. Both were generated from different sources at different times.**

---

## The Solution: Model B — Derived Promoted to SSOT

We designed a model where:

1. **Generated artifacts become the single source of truth**
2. **Cryptographic integrity is enforced**
3. **Only one command can modify the bundle**
4. **Gates verify integrity on every change**

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SHA-256 checksums | Industry standard, fast, reliable |
| Single writer command | Prevents parallel modification |
| YAML manifest as SSOT | Human-readable, versionable |
| L0/L1/L2 gates | Progressive validation depth |

---

## Evolution: L0 → L2

### L0 — Structure (✅ Complete)
- Files exist
- Valid YAML/JSON/SQL syntax
- Basic presence check

### L1 — Schema (✅ Complete)
- Consistency between schema.sql and openapi.json
- No structural drift between artifacts

### L2 — Integrity (✅ Complete)
- SHA-256 checksums against manifest
- Single-writer enforcement
- Deterministic regeneration verified

### L3 — Evidence (Reserved)
- Commit binding
- Evidence packs
- Baseline diffing
- **Trigger:** Multi-contributor or CI-driven generation

### L4 — Runtime (Reserved)
- Runtime determinism validation
- **Trigger:** Autonomous agents modifying docs

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌────────┐
│  Generator  │ ──► │   Snapshot   │ ──► │ Integrity       │ ──► │ Gate   │
│  (Python)   │     │  (Artifacts) │     │ Manifest (YAML) │     │(L0-L2) │
└─────────────┘     └──────────────┘     └─────────────────┘     └────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Generator | `scripts/generate/docs/gen_docs_soot.py` | Produces schema.sql, openapi.json |
| Writer | `docs/_ssot/update_gen.ps1` | Single authorized command |
| Manifest | `docs/_ssot/_manifest.yaml` | Checksum SSOT |
| Gate | `scripts/checks/check_hb_track_profile.py` | L0-L2 validation |

---

## Usage

### Generating Documentation

```powershell
pwsh docs/_ssot/update_gen.ps1
```

This produces:
- `docs/_ssot/schema.sql`
- `docs/_ssot/openapi.json`
- `docs/_ssot/alembic_state.txt`
- `docs/_ssot/_manifest.yaml` (updated checksums)

### Validating Integrity

```powershell
pwsh scripts/checks/check_hb_profile.ps1
```

Or directly:

```python
python scripts/checks/check_hb_track_profile.py
```

### Checking Baseline Drift

```python
python scripts/checks/check_determinism_baseline.py --baseline docs-determinism-v1
```

---

## What We Learned

### 1. Determinism is Hard to Build, Easy to Break

The initial implementation required:
- 3 iterations to get the gate logic right
- Multiple false positives fixed
- Schema consistency verification added

### 2. Single-Writer is Crucial

Without enforcing a single command, parallel modifications would create conflicts. The writer script is the **only** path to modify artifacts.

### 3. Gates Must Be Fast

If gates take too long, developers skip them. Our gates run in <5 seconds.

### 4. Documentation Needs Versioning

Treating the manifest as SSOT meant we needed baseline snapshots. This led to `docs-determinism-v1`.

---

## Comparison with Industry

| Maturity Level | Description | Most Projects |
|----------------|-------------|---------------|
| README-driven | Basic readme | Common |
| Docs-as-code | Markdown in repo | Intermediate |
| Schema-driven docs | JSON Schema validation | Advanced |
| Deterministic docs | Cryptographic integrity | Rare |
| Cryptographic integrity docs | Full audit trail | Very Rare |

**HB Track is at level 4** — deterministic documentation with cryptographic integrity.

---

## Future Evolution

### When to Advance to L3

- Multiple contributors generating snapshots
- CI/CD driving documentation regeneration
- Audit trail requirements
- Autonomous agents modifying documentation

### When to Stay at L2

- Single maintainer
- Low documentation change frequency
- No compliance requirements

**Recommendation:** Stay at L2 until triggers appear. Premature abstraction adds complexity.

---

## References

| Resource | Location |
|----------|----------|
| Baseline | `docs/_canon/BASELINES/docs-determinism-v1.md` |
| SPEC | `docs/_canon/SPECS/SPEC_MODEL_B_DERIVED_PROMOTED_SSOT.md` |
| Status | `docs/_canon/STATUS/docs_determinism_status.md` |
| Writer | `docs/_ssot/update_gen.ps1` |
| Gate | `scripts/checks/check_hb_track_profile.py` |

---

## Conclusion

Deterministic documentation isn't just a technical achievement — it's a **trust infrastructure**. When you know that your documentation exactly matches your code, you can:

- **Move faster** (trust the contracts)
- **Refactor safely** (detect drift immediately)
- **Scale with AI** (agents can't hallucinate over protected artifacts)

The investment pays dividends in reduced bugs, faster onboarding, and reliable automation.

---

*This document is part of the HB Track documentation governance system. For questions, consult `docs/_canon/ARCHITECT_HANDSHAKE.md`.*
