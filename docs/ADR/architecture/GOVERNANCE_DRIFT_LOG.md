# Governance Drift Log (HB Track)

Este documento registra divergências entre a governança pretendida (ADRs/Protocolos) e a execução real observada, servindo como backlog para "Detection Hardening" e refinamento de processos.

---

## DRIFT-STATUS-VOCAB-001 (2026-02-13)
- **Status:** OPEN (Pending Normalization)
- **Descrição:** Uso de estados ad-hoc no campo `status` de `event.json` (ex: `PASS_WITH_EVIDENCE_GAPS_NOTED`) que quebram scripts de automação.
- **Risco:** Falha na indexação automática e bloqueio de auditoria.
- **Contenção:** Restringir `status` aos valores canônicos `{PASS, FAIL, DRIFT}`.

---

## GOVERNANCE GAPS (Active Inventory)

### [GAP-ASTREG-PATH-001]
- **Tarefa:** ARCH-AST-REG-001
- **Descrição:** Ausência de paths canônicos completos nos reports de auditoria.
- **Disposição:** RECORDED

### [GAP-ASTREG-INDEXSNAP-001]
- **Tarefa:** ARCH-AST-REG-001
- **Descrição:** Falta de snapshots integrais de CHANGELOG/EXECUTIONLOG no Evidence Pack.
- **Disposição:** RECORDED
