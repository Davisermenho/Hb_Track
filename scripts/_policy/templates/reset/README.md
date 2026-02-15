# Template: reset/

## Purpose

Destructive operations (reset DB/env/services).

- **DANGER**: Not recoverable without backups

## MUST

- Require explicit confirmation flag (`-Force` / `--force`)
- Print a clear **[DESTRUCTIVE]** banner
- Provide rollback notes (even if "restore from backup")

## MAY

- ENV_WRITE and DB_WRITE

## MUST NOT

- Proceed silently. Always require `-Force` to execute.

## Agent Notes

- Always default to safe mode: refuse without `-Force`
- Print banner to stderr: `[DESTRUCTIVE] Operation will delete <X>`
- Use stratified naming: `reset_{{SCOPE}}__{{ACTION}}.py`
