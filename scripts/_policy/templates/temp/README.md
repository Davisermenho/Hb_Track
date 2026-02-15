# Template: temp/

## Purpose

Quarantine for unstable/experimental scripts.

- **MUST be gitignored**
- **MUST use `tmp_` prefix**
- **MUST NOT be referenced by run/ wrappers**

## SHOULD

- Be promoted if used repeatedly or required by a task
- Graduated to the correct category when stabilized

## Agent Notes

- If a temp script becomes necessary for production, promote it to the correct category
- Rename on promotion: `tmp_{{ACTION}}.py` → `{{KIND}}_{{SCOPE}}__{{ACTION}}.py`
- Use category-specific SIDE_EFFECTS and RISK only after promotion
