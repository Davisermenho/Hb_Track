# Template: ops/

## Purpose

Operational maintenance (refresh views, maintenance SQL, infra tasks).

- Manual by default (not auto-run)

## MUST

- Require explicit flags (e.g., `--apply` / `-Force`) for writes
- Be safe-by-default (dry-run unless confirmed)

## MAY

- DB_WRITE and/or ENV_WRITE

## MUST NOT

- Destructive resets (belongs to reset/)

## Agent Notes

- Always print: `[OPS] apply=<true/false>`
- Use stratified naming: `ops_{{SCOPE}}__{{ACTION}}.py`
