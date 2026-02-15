# Template: migrate/

## Purpose

Evolve data (backfill, legacy import, one-off data migrations).

- **NOT schema migrations** (those are Alembic)

## MUST

- Be explicit about scope (backfill/legacy/oneoff)
- Provide rollback guidance if possible
- Never auto-run in CI unless explicitly controlled

## MAY

- DB_WRITE

## MUST NOT

- ENV_WRITE (belongs to ops/reset)

## Agent Notes

- Prefer chunking + resumability (idempotent markers)
- Always print a summary line: `[MIGRATE] rows affected=<n>`
- Use stratified naming: `mig_{{SCOPE}}__{{ACTION}}.py`
