# PHASE D — CONSOLIDATION PLAN (BATCH 002)

**Date:** 2026-02-14  
**Status:** APPROVED_FOR_EXECUTION  
**Scope:** Models pipeline docs + SSOT path alignment (`docs/_generated/schema.sql`)

---

## Objective

Reduzir drift e inconsistência cruzada no tópico **Models Pipeline** (Guard/Parity/Requirements), consolidando documentação operacional duplicada e removendo ambiguidades de SSOT.

**SSOT declarado para este batch:** `docs/_generated/schema.sql` (repo root).

---

## Consolidation Mapping (Origin -> Destination)

1. `docs/scripts/VERIFY_MODELS.md`
   - Destino: `docs/_canon/05_MODELS_PIPELINE.md`
     - incorporar somente o que agrega (mapa de scripts, checklist pré-voo, SSOT path policy)
     - corrigir inconsistências (ex.: baseline local vs commitável; links absolutos; fences quebradas)
   - Ação final: **remover** `docs/scripts/VERIFY_MODELS.md`

2. `docs/_canon/04_SOURCES_GENERATED.md`
   - Atualizar para:
     - referenciar `docs/_generated/schema.sql` como path canônico
     - apontar regeneração via `scripts/inv.ps1 refresh` (sem “verificar em docs/scripts/” genérico)
     - remover links absolutos (`C:/HB TRACK/...`) em favor de paths repo-relativos

3. `scripts/inv.ps1` (refresh/ssot)
   - Harden: validar também os artefatos em `docs/_generated/*` (repo root) após rodar `generate_docs.py`, garantindo que o SSOT declarado existe e está sincronizado com o backend.

---

## Backward Compatibility

- Não há dependências conhecidas de `docs/scripts/VERIFY_MODELS.md` em scripts/workflows. Como mitigação, executar busca por referências antes de remover.
- Compatibilidade de execução permanece: scripts do backend continuam usando `Hb Track - Backend/docs/_generated/*` (mirror), enquanto o SSOT canônico é `docs/_generated/*`.

---

## Gates (Must Pass)

1. `python3 docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml` exit `0`
2. `python3 docs/scripts/_ia/generate_ai_governance_index.py --write` exit `0`
3. `python3 docs/scripts/_ia/generate_ai_governance_index.py --check` exit `0`
4. `python3 docs/scripts/_ia/ai_governance_linter.py` exit `0` (se não for viável localmente, reexecutar em CI e registrar evidência)

---

## Stop Conditions

- Se qualquer gate falhar: **STOP** e corrigir antes de prosseguir.
- Se for encontrado uso explícito de `docs/scripts/VERIFY_MODELS.md` em workflow/script: **STOP**, atualizar referências e só então remover.
- Se `inv.ps1 refresh` não gerar e validar `docs/_generated/schema.sql`: **STOP** (SSOT deste batch é inválido).

