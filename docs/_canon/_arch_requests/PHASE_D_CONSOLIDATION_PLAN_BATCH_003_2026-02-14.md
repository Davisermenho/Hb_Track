# PHASE D — CONSOLIDATION PLAN (BATCH 003)

**Date:** 2026-02-14  
**Status:** APPROVED_FOR_EXECUTION  
**Scope:** Canonical docs link hardening + semantic consolidation (governance hierarchy)

---

## Objectives

1. Eliminar **links absolutos** (ex.: `C:/HB TRACK/...`) em documentação canônica/operacional, trocando por paths repo-relativos.
2. Reduzir fragmentação por **consolidação semântica** sem perda de informação normativa.

---

## Consolidation Mapping (Origin -> Destination)

1. `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md` (manual, hierarquia normativa)
   - Destino: `docs/_canon/GOVERNANCE_MODEL.md`
     - mover: hierarquia normativa (LEVEL 0-4), regras de precedência, conflito, integridade e amendment rule
     - ajustar: referências para apontar para o índice auto-gerado (`docs/_canon/AI_GOVERNANCE_INDEX.md`)
   - Ação final: **remover** `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md`

---

## Absolute Link Remediation (C:/HB TRACK -> repo-relative)

Atualizar referências em (mínimo):

- `docs/_canon/01_AUTHORITY_SSOT.md`
- `docs/_canon/02_CONTEXT_MAP.md`
- `docs/ADR/_INDEX_ADR.md`
- `docs/ADR/018-ADR-DOCS-governance-unification.md`
- `docs/references/model_requirements_guide.md`
- `.github/prompts/*.prompt.md`

Regra: substituir links `](C:/HB TRACK/<path>)` por paths repo-relativos (sem depender de `C:\...`).

---

## Backward Compatibility

- Atualizar todos os arquivos que referenciam `docs/_canon/_agent/AI_GOVERNANCE_INDEX.md` para os novos SSOTs:
  - Índice auto-gerado: `docs/_canon/AI_GOVERNANCE_INDEX.md`
  - Hierarquia normativa: `docs/_canon/GOVERNANCE_MODEL.md`

---

## Gates (Must Pass)

1. `python3 docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml` exit `0`
2. `python3 docs/scripts/_ia/generate_ai_governance_index.py --write` exit `0`
3. `python3 docs/scripts/_ia/generate_ai_governance_index.py --check` exit `0`
4. `python3 docs/scripts/_ia/ai_governance_linter.py` exit `0`

---

## Stop Conditions

- Se qualquer gate falhar: **STOP** e corrigir antes de prosseguir.
- Se algum link ficar quebrado (arquivo alvo inexistente): **STOP** e corrigir referência.
- Se for detectada dependência operacional de path removido: **STOP** e criar compat layer (redirect) ou ajustar scripts.

