# Template: seeds/

## Purpose

Populate baseline data (official/test/dev).

- Must be deterministic or explicitly labeled as non-deterministic

## MUST

- Place seeds under: `dev/` `official/` `test/` (or `_archived/`)
- **official/** must be minimal and reproducible

## MAY

- DB_WRITE

## MUST NOT

- Depend on time/random without fixed seed & explicit _labeling

## Agent Notes

- Prefer SQL seeds for minimal SSOT-like behavior
- Use stratified naming: `seed_{{SCOPE}}__{{ACTION}}.py`
- Tag non-deterministic scripts: `_nondeterministic_` prefix if needed
