# Template: run/

## Purpose

Wrappers/orchestration entrypoints only.

- **NO business logic**

## MUST

- Call scripts from other categories
- Prepare env/args, set working dir, capture logs to artifacts
- Be stable and human-friendly

## MUST NOT

- Implement domain logic
- Reference `scripts/temp/`

## Agent Notes

- Use deterministic ordering (sort targets)
- Use consistent exit code propagation
- Use stratified naming: `run_{{ACTION}}.py`
