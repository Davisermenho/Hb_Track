# TASK_BRIEF: ARCH-GOV-STATUS-VOCAB-001

## 1. Contexto & Motivação
O script de compactação de logs (`compact_exec_logs.py`) falhou ao processar tarefas com o status `PASS_WITH_EVIDENCE_GAPS_NOTED`. Este status foi introduzido para sinalizar tarefas técnica aprovadas mas com lacunas documentais/evidência, porém violou o schema restritivo `ALLOWED_STATUS = {"PASS", "FAIL", "DRIFT"}`.

## 2. Objetivos
- Normalizar o vocabulário de status nos arquivos `event.json`.
- Garantir que as tarefas `ARCH-AST-001` e `ARCH-AST-REG-001` sejam indexadas corretamente.
- Registrar formalmente o drift de vocabulário e os gaps de evidência herdados.

## 3. Drift & Gaps (SSOT)
### DRIFT-STATUS-VOCAB-001
- **Status:** OPEN
- **Trigger:** Aviso de validação no compactador de logs.
- **Contenção:** `event.json` deve manter `status` ∈ {PASS, FAIL, DRIFT}. Qualificadores vão para campos descritivos.

### GOVERNANCE_GAPS
- GAP-ASTREG-PATH-001: Paths canônicos ausentes.
- GAP-ASTREG-INDEXSNAP-001: Snapshots integrais ausentes.

## 4. Plano de Ação
1. Alterar `ARCH-AST-001/event.json` e `ARCH-AST-REG-001/event.json`: `status` -> `PASS`.
2. Adicionar prefixo `(Audit: Gaps Noted)` ao `notes_short` ou `short_title`.
3. Executar `compact_exec_logs.py` e validar saída.
4. Criar `docs/ADR/architecture/GOVERNANCE_DRIFT_LOG.md` como registro centralizado.

## 5. Critérios de Aceite
- [ ] `compact_exec_logs.py` retorna Exit 0.
- [ ] `CHANGELOG.md` e `EXECUTIONLOG.md` contém as tarefas normalizadas.
- [ ] Repositório limpo e commitado.
