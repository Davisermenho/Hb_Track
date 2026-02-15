# AUDIT_SCRIPTS_DOCS_REPORT — AR-2026-02-13-SCRIPTS-DOCS-AUDIT

Status: BASELINE_AUDIT_COMPLETED
Date: 2026-02-13
Source ARCH_REQUEST: `docs/_canon/_arch_requests/AR-2026-02-13-SCRIPTS-DOCS-AUDIT.md`

---

## 1) Escopo auditado

Diretórios auditados (nome `scripts` e documentação relacionada):

- `scripts/`
- `docs/scripts/`
- `Hb Track - Backend/scripts/`
- `Hb Track - Fronted/scripts/`

Evidência de inventário: listagens coletadas em sessão ACT (tools `list_files`).

---

## 2) Critério de decisão por arquivo

Classificações permitidas:

- `INCORPORAR`
- `REFATORAR_ANTES_DE_INCORPORAR`
- `DIVIDA_TECNICA`
- `ARQUIVAR`

Regras aplicadas:

1. Sem interface CLI mínima (`--tenant-id`, `--dry-run`, `--output json`) => não incorpora diretamente.
2. Sem logs estruturados JSON => não incorpora diretamente.
3. Fix/migração sem evidência de idempotência => `DIVIDA_TECNICA`.
4. Artefato legado/backup/duplicado => `ARQUIVAR` (sem delete físico).

---

## 3) Scripts críticos (smoke test)

1. `scripts/inv.ps1`
2. `scripts/run_invariant_gate.ps1`
3. `scripts/run_invariant_gate_all.ps1`
4. `Hb Track - Backend/scripts/parity_scan.ps1`
5. `Hb Track - Backend/scripts/parity_gate.ps1`
6. `Hb Track - Backend/scripts/models_autogen_gate.ps1`
7. `Hb Track - Backend/scripts/models_batch.ps1`
8. `Hb Track - Backend/scripts/model_requirements.py`
9. `Hb Track - Backend/scripts/agent_guard.py`
10. `Hb Track - Fronted/scripts/sync_openapi.ps1`

---

## 4) Matriz de decisão (baseline)

## 4.1 `scripts/` (repo root)

| Arquivo | Decisão | Justificativa |
|---|---|---|
| `inv.ps1` | INCORPORAR | Script core de orquestração já canônico no fluxo operacional |
| `run_invariant_gate.ps1` | INCORPORAR | Gate operacional oficial |
| `run_invariant_gate_all.ps1` | INCORPORAR | Gate global oficial |
| `compact_exec_logs.py` | REFATORAR_ANTES_DE_INCORPORAR | Falta contrato explícito de interface/log JSON |
| `docs/scripts/_ia/**/*.py` | REFATORAR_ANTES_DE_INCORPORAR | Ferramentas relevantes, porém sem contrato uniforme único |
| `docs/scripts/_ia/logs/*` | ARQUIVAR | Artefatos de execução/histórico, não scripts operacionais |

## 4.2 `docs/scripts/`

| Arquivo/Grupo | Decisão | Justificativa |
|---|---|---|
| `gates/adr_required_gate.ps1` | REFATORAR_ANTES_DE_INCORPORAR | Relevante, requer padronização de interface/log |
| `verify_invariants_tests.py` | REFATORAR_ANTES_DE_INCORPORAR | Relevante para qualidade, falta contrato mínimo |
| `*.BACKUP_*`, `*.bak_*`, `validation_*.txt`, `report.txt` | ARQUIVAR | Legado/backup/saída textual sem função operacional primária |
| `tests/test_ast_analyzer.py` | INCORPORAR | Artefato de teste válido (não script operacional), manter em trilha de qualidade |

## 4.3 `Hb Track - Backend/scripts/`

| Grupo | Decisão | Justificativa |
|---|---|---|
| `parity_*.ps1`, `models_*.ps1`, `model_requirements.py`, `agent_guard.py` | INCORPORAR | Núcleo canônico de compliance e pipeline model↔schema |
| `seed_*.py`, `fix_*.py`, `apply_migration_*.py`, `create_*.py` | DIVIDA_TECNICA | São scripts de mutação; exigem validação formal de idempotência |
| `test_*.py`, `validate_*.py`, `check_*.py` | REFATORAR_ANTES_DE_INCORPORAR | Úteis para diagnóstico, mas sem contrato uniforme de CLI/log |
| `*.bak` | ARQUIVAR | Backup legado |

## 4.4 `Hb Track - Fronted/scripts/`

| Arquivo | Decisão | Justificativa |
|---|---|---|
| `sync_openapi.ps1` | INCORPORAR | Script crítico de sincronização contrato API |
| `validate-staging.ps1` | REFATORAR_ANTES_DE_INCORPORAR | Relevante, requer JSON logging padronizado |
| `eslint-triage.mjs`, `hygiene-check.mjs`, `hygiene-diff.mjs` | REFATORAR_ANTES_DE_INCORPORAR | Relevantes para qualidade, faltam parâmetros padrão e saída JSON unificada |

---

## 5) Plano de reorganização segura (_archived)

Padrão aprovado:

- `_archived/YYYY-MM-DD/<domain>/...`

Aplicação:

1. Mover apenas arquivos classificados `ARQUIVAR`.
2. Nunca remover fisicamente arquivos em auditoria.
3. Registrar em changelog do PR: origem, destino, motivo.

---

## 6) Resultado desta execução

- ARCH_REQUEST canônica criada.
- `SCRIPTS_GUIDE.md` canônico criado com contrato enterprise.
- `00_START_HERE.md` atualizado para roteamento da governança de scripts.
- `.gitignore` atualizado para política de `_archived/`.
- Auditoria baseline registrada neste relatório.

> Nota: Esta entrega estabelece a base documental + matriz de decisão. A migração física de arquivos para estrutura funcional deve ocorrer em lote controlado (com smoke tests dos scripts críticos entre lotes).
