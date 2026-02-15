# SSOT Root Map (Canonical)

**Status:** CANONICAL  
**Version:** 1.0.0  
**Last Updated:** 2026-02-14  
**Authority:** `docs/_canon/00_START_HERE.md` + `docs/_canon/PATHS_SSOT.yaml`

---

## Purpose

Definir **root canônico por função documental/operacional**, reduzindo ambiguidade e drift.

Regra obrigatória: conteúdo de uma função **MUST** ficar no seu root canônico.  
Exceções só são válidas via atualização explícita de `PATHS_SSOT.yaml`.

---

## Canonical Roots By Function

| Função | Root Canônico |
|---|---|
| Governança canônica | `docs/_canon` |
| Operação de agentes (docs) | `docs/_ai` |
| ADRs | `docs/ADR` |
| Execution tasks | `docs/execution_tasks` |
| Artefatos gerados | `docs/_generated` |
| Scripts documentais/governança | `docs/scripts` |
| Instruções de agente | `.github/instructions` |
| Prompts operacionais | `.github/prompts` |
| Protocolos de agentes | `.github/agents` |
| Workflows CI/CD | `.github/workflows` |

---

## Function-Specific Location Rules

1. Arquivos `*.instructions.md` devem residir em `.github/instructions`.
2. Arquivos `*.prompt.md` devem residir em `.github/prompts`.
3. Arquivos `AR-*`, `VALIDATION_MUST_REPORT_*`, `STATUS_DASHBOARD_*`, `DUAL_EXECUTION_PLAN_*`, `SESSION_SUMMARY_*` devem residir em `docs/_canon/_arch_requests`.
4. Arquivos `EXEC_TASK*` devem residir em `docs/execution_tasks`.
5. Arquivos ADR (`ADR-*.md`, `NNN-ADR-*.md`) devem residir em `docs/ADR`.
6. Scripts centrais de governança (`ai_governance_linter.py`, `lint_arch_request.py`, `generate_ai_governance_index.py`, `check_logs_compaction.py`) devem residir em `docs/scripts/_ia`.
7. `scripts/_ia/**/*.py` é caminho legado proibido para código operacional (logs legados podem permanecer durante transição).

---

## Paths SSOT

Fonte única de paths: `docs/_canon/PATHS_SSOT.yaml`.

Toda automação/gate de localização **MUST** ler esta fonte e não hardcodar roots em múltiplos arquivos.

---

## Validation Gate

Comando canônico:

```bash
python3 docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml
```

Exit codes:

- `0`: conformidade total.
- `2`: violação de política de root/localização.
- `1`: erro interno de execução/configuração.

---

## Change Protocol

Qualquer alteração de roots/regras requer:

1. Atualizar `docs/_canon/PATHS_SSOT.yaml`.
2. Atualizar este documento se houver mudança semântica.
3. Executar gate `validate-ssot-roots.py`.
4. Registrar em changelog/artefato de execução aplicável.
