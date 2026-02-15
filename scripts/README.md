# HB Track - Backend Scripts

Pasta centralizada para scripts operacionais, de manutenção e automação.

## CANONICAL ENTRYPOINTS (CI + Local)

Estes são os **únicos** comandos oficiais para validação de governance:

| Gate | Comando | SSOT | Engine |
|------|---------|------|--------|
| **R12: Python Layout** | `pwsh -File scripts/checks/lint/check_python_layout.ps1` | [python_layout.policy.yaml](../_policy/python_layout.policy.yaml) | [check_python_layout.py](../_policy/check_python_layout.py) |
| **Scripts Policy** | `pwsh -File scripts/checks/policy/check_scripts_policy.ps1` | [scripts.policy.yaml](../_policy/scripts.policy.yaml) | [check_scripts_policy.ps1](../_policy/check_scripts_policy.ps1) |
| **Manifest Integrity** | `pwsh -File scripts/checks/policy/check_policy_manifest.ps1` | [policy.manifest.json](../_policy/policy.manifest.json) | [check_policy_manifest.ps1](../_policy/check_policy_manifest.ps1) |
| **Derived MD Drift** | `pwsh -File scripts/checks/policy/check_policy_md_is_derived.ps1` | [scripts.policy.yaml](../_policy/scripts.policy.yaml) | [check_policy_md_is_derived.ps1](../_policy/check_policy_md_is_derived.ps1) |

**Exit codes (all gates):**
- `0` = OK (compliance)
- `2` = VIOLATION / MISMATCH / DRIFT (policy/data error)
- `3` = HARNESS_ERROR (missing deps, git issue, etc.)

## Regra Determin�stica (MANDAT�RIA)
- **scripts/checks/**: Estritamente **READ-ONLY**. Scripts aqui n�o podem alterar banco de dados, arquivos ou estados do sistema.
- **scripts/fixes/**: Scripts que aplicam corre��es ou patches.
- **scripts/run/**: Ponto de entrada para automa��o (PowerShell).

## Estrutura
- **artifacts/**: Sa�das de scripts (ignorados pelo git, exceto README).
- **diagnostics/**: Scripts de an�lise profunda (Read-only mais complexos).
- **generate/**: Geradores de c�digo, hashes, schemas.
- **migrate/**: Migra��es de dados e backfills.
- **ops/**: Opera��es de infraestrutura e banco (maintenance/refresh).
- **reset/**: Scripts para resetar ambiente ou servi�os.
- **security/**: Auditorias e corre��es de seguran�a.
- **seeds/**: Popula��o de dados (dev/test/official).
- **temp/**: Scripts tempor�rios e testes locais (ignorados pelo git).
