# IMPLEMENTATION REPORT — PHASE D (BATCH 003)

**Date:** 2026-02-14  
**Status:** COMPLETE_PASS  
**Batch:** 003 (Absolute link remediation + governance hierarchy consolidation)

---

## Objective

1. Eliminar links absolutos (`C:/HB TRACK/...`) em docs canônicos/operacionais, reduzindo acoplamento ao ambiente local e aumentando portabilidade.
2. Reduzir fragmentação por consolidação semântica sem perda de autoridade normativa.

---

## Changes

### A) Consolidação semântica (redução de arquivos)

- Consolidado conteúdo normativo de hierarquia/precedência (antigo):
  - `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md`
  - Em: `docs/_canon/GOVERNANCE_MODEL.md`
- Removido arquivo redundante/ambíguo:
  - `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md`

### B) Atualização de referências (compat)

- Atualizadas referências para os SSOTs atuais:
  - Hierarquia normativa: `docs/_canon/GOVERNANCE_MODEL.md`
  - Índice auto-gerado: `docs/_canon/AI_GOVERNANCE_INDEX.md`
- Arquivos atualizados (principais):
  - `docs/_ai/_INDEX.md`
  - `docs/_ai/_guardrails/GUARDRAILS_INDEX.md`
  - `docs/_canon/_agent/GOVERNANCE_AUDIT_REPORT.md`
  - `docs/_canon/_agent/WHEN_TO_USE_TASK_BRIEF.md`
  - `docs/ADR/018-ADR-DOCS-governance-unification.md`

### C) Remoção de links absolutos (C:/HB TRACK → repo-relative)

Atualizado (mínimo):
- `docs/_canon/01_AUTHORITY_SSOT.md`
- `docs/_canon/02_CONTEXT_MAP.md` (inclui correção de referências inexistentes → `_INDEX_ADR.md` quando aplicável)
- `docs/ADR/_INDEX_ADR.md` (inclui correção do nome do ADR-016 para `016-ADR-machine-readable-ai-quality-gates.md`)
- `docs/ADR/018-ADR-DOCS-governance-unification.md`
- `docs/references/model_requirements_guide.md`
- `docs/02_modulos/training/PROTOCOLS/PARITY_SCAN._PROTOCOL.md`
- `docs/02_modulos/training/INVARIANTS/INVARIANTS_TRAINING.md`
- `docs/02_modulos/training/INVARIANTS/INVARIANTS_TESTING_CANON.md`
- `.github/prompts/parity-fix.prompt.md`
- `.github/prompts/generate-exec-task.prompt.md`
- `.github/prompts/models-gate.prompt.md`
- `.github/instructions/doc.script.instructions.md` (applyTo sem paths absolutos)
- `.github/instructions/rules.instructions.md` (restore sem `C:/...`)
- `.github/instructions/tabelas.instructions.md` (restore sem `C:/...`)
- `docs/_canon/_agent/EVIDENCE_PACK.md` (template: remove placeholders absolutos)
- `docs/execution_tasks/EXEC_TASK_ADR_MODELS_014.md` (referências iniciais em formato repo-relative)

### D) Gate fix (lint compat)

- `docs/_canon/_arch_requests/AUTH-CONTEXT-SSOT-002.md`:
  - renomeado heading de aceite para incluir `GATES` (necessário para `lint_arch_request.py` compat profile)

### E) Hardening (portabilidade)

- `docs/scripts/_ia/check_logs_compaction.py`:
  - remove hardcode `C:/HB TRACK/...`
  - passa a resolver `docs/execution_tasks/artifacts` a partir do repo root (via `.git`)

---

## Gates Executados (evidência)

1. SSOT roots:

```bash
python3 docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml
```

- Exit: `0`

2. Governance index:

```bash
python3 docs/scripts/_ia/generate_ai_governance_index.py --write
python3 docs/scripts/_ia/generate_ai_governance_index.py --check
```

- Exit: `0`

3. AI governance linter:

```bash
python3 docs/scripts/_ia/ai_governance_linter.py
```

- Exit: `0`

---

## Notes

- A remoção de links absolutos reduz drift por ambiente local e melhora a navegação em GitHub/CI.
- A remoção de `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md` elimina ambiguidade com o índice auto-gerado `docs/_canon/AI_GOVERNANCE_INDEX.md`.
