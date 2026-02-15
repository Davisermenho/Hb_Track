# Template: checks/

## Purpose

Deterministic gates with mandatory exit code contract:
- **0** = PASS (invariant satisfied)
- **2** = FAIL (invariant violated / check failed)
- **3** = HARNESS ERROR (misconfiguration / cannot run)

## MUST

- **READ-ONLY only** (DB_READ, FS_READ, NONE)
- **Deterministic** (same inputs => same outputs + exit code)
- Write outputs (if any) ONLY under `scripts/artifacts/checks/...`

## MUST NOT

- DB_WRITE, FS_WRITE (except artifact outputs), ENV_WRITE, NET

## Agent Notes

- Prefer reading SSOT (`docs/_generated/*`, config) over derived artifacts
- If env missing (e.g. DATABASE_URL), exit 3 with a single-line summary
- Use stratified naming: `check_{{SCOPE}}__{{ACTION}}.py` → `check_athletes__integrity.py`
