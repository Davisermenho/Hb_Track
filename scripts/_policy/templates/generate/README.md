# Template: generate/

## Purpose

Generate deterministic derived artifacts (hashes/docs/dumps).

- **Outputs are derived, NOT SSOT** (see `docs/_generated/` for canonical examples)

## MUST

- Be idempotent (same inputs => same outputs)
- Produce deterministic outputs
- Write outputs to intended targets (often `docs/_generated/*` and/or `scripts/artifacts/generate/...`)

## MUST NOT

- "Fix drift" (belongs to fixes/)
- DB_WRITE unless explicitly justified by SSOT and documented

## Agent Notes

- If outputs include timestamps, keep them in a footer/comment, not in the content hash surface
- Use stratified naming: `gen_{{SCOPE}}__{{ACTION}}.py`
