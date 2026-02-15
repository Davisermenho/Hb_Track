# Template: fixes/

## Purpose

Correct drift (code/DB/files). **Not gates**, but corrections.

## MUST

- Log effects to `scripts/artifacts/fixes/...` (diffs, summaries)
- Be explicit about what changed
- **NEVER** hide side effects. Silent changes are forbidden.

## SHOULD

- Be idempotent (re-running results in no-op or stable outcome)
- Provide rollback hints when applicable

## MAY

- DB_WRITE and/or FS_WRITE

## Agent Notes

- If a fix changes versioned files, output a summary line: `[FIX] <what> <files>`
- If cannot proceed safely, exit non-zero and explain
- Use stratified naming: `fix_{{SCOPE}}__{{ACTION}}.py`
