# Template: diagnostics/

## Purpose

Human triage scripts (not required for gates or CI).

- **READ-ONLY** inspection
- Local debug / manual analysis

## MUST

- Be **READ-ONLY** (DB_READ, FS_READ, NONE)
- Be safe to run locally (no destructive side effects)

## MAY

- Produce verbose outputs under `scripts/artifacts/diagnostics/...`

## MUST NOT

- DB_WRITE, FS_WRITE (except artifacts), ENV_WRITE, NET

## Agent Notes

- Diagnostics can print more context; still avoid non-deterministic timestamps unless needed
- Prefer exit 0 on success; use exit 3 for harness errors
- Use stratified naming: `diag_{{SCOPE}}__{{ACTION}}.py`
