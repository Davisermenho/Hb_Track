# PHASE D — CONSOLIDATION PLAN (BATCH 001)

**Date:** 2026-02-14  
**Status:** APPROVED_FOR_EXECUTION  
**Scope:** `.github/instructions/**` (low-risk, governance-only)

---

## Objective

Reduzir fragmentação e drift em instruções operacionais, mantendo 100% da funcionalidade.

Batch 001 foca em um caso claro de redundância/legado:

- `.github/instructions/comands.instructions.md` (nome incorreto + conteúdo muito amplo, parte duplicado do canônico)

---

## Consolidation Mapping (Origin -> Destination)

1. `.github/instructions/comands.instructions.md`
   - Destino A: `.github/instructions/00_general.instructions.md`
     - mover: fontes obrigatórias + regras globais (sem duplicar o que já está em `docs/_canon/00_START_HERE.md`)
   - Destino B: `.github/instructions/03_commands.instructions.md`
     - mover: regras de shell/CWD/quoting e política anti-destruição (relacionadas a execução de comandos)
   - Ação final: **remover** `comands.instructions.md`

---

## Backward Compatibility

- Nenhum script/workflow deve depender de `comands.instructions.md` pelo nome.
- Como mitigação, as regras serão preservadas em 2 arquivos já carregados globalmente (`applyTo: "**"`).

---

## Gates (Must Pass)

1. `python3 docs/scripts/validate-ssot-roots.py --config docs/_canon/PATHS_SSOT.yaml` exit `0`
2. `python3 docs/scripts/_ia/ai_governance_linter.py` exit `0`
3. `python3 docs/scripts/_ia/generate_ai_governance_index.py --write` exit `0`
4. `python3 docs/scripts/_ia/generate_ai_governance_index.py --check` exit `0`

---

## Stop Conditions

- Se qualquer gate acima falhar: **STOP** e reverter o batch.
- Se for encontrado uso explícito do path removido em algum workflow/script: **STOP** e atualizar referências antes de remover.

