# Templates (Shared)

These templates are used by `scripts/run/run_new_script.ps1` (or any scaffolder)
to create new scripts with deterministic headers (`HB_SCRIPT_*`).

## Rules

- The SSOT for rules is `scripts/_policy/scripts.policy.yaml`.
- The derived doc is `scripts/scripts_classification.md`.
- Any executable script under `scripts/` MUST include the required `HB_SCRIPT_*` header.
- Category-specific templates override shared defaults.

## Placeholders

- `{{KIND}}` — Script classification (CHECK, FIX, GENERATE, etc.)
- `{{SCOPE}}` — Scope name (e.g., "models", "db", "infra")
- `{{SIDE_EFFECTS}}` — Operational side effects (DB_READ, FS_WRITE, etc.)
- `{{IDEMPOTENT}}` — YES / NO
- `{{ENTRYPOINT}}` — Full invocation command
- `{{OUTPUTS}}` — Output artifacts location
- `{{INPUTS}}` — Input parameters (optional)
- `{{RISK}}` — Risk level (LOW, MEDIUM, HIGH)
- `{{ROLLBACK}}` — Rollback instructions (optional)

## Language-Specific Syntax

- **Python**: `# HB_SCRIPT_*` comments
- **PowerShell**: `<# HB_SCRIPT_* #>` block comments
- **SQL**: `-- HB_SCRIPT_*` line comments
