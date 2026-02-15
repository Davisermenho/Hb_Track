# INVARIANTS — AGENT GUARDRAILS (LOCAL-FIRST)

> **Parent:** [`_guardrails/GUARDRAILS_INDEX.md`](_guardrails/GUARDRAILS_INDEX.md) (Entry point único para todos os guardrails)  
> **Domain:** Invariants Guardrails (Training Module — INV-TRAIN-XXX gates)  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13

Este repositório usa gates para impedir alucinação: nenhuma invariante é considerada instalada/alterada sem evidência do gate.

## SSOT (Fontes canônicas)
- `Hb Track - Backend/docs/_generated/openapi.json`
- `Hb Track - Backend/docs/_generated/schema.sql`
- `Hb Track - Backend/docs/_generated/alembic_state.txt`
- `docs/02-modulos/training/INVARIANTS_TRAINING.md`
- `docs/scripts/verify_invariants_tests.py`

**Regra**: se houver divergência, SSOT vence. Não inventar contrato.

**Atualizar SSOT (recomendado antes de promoções):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 refresh
```

---

## COMANDOS CANÔNICOS (usar o wrapper)

**Refresh SSOT (regenera os 3 artefatos canônicos):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 refresh
# Alias: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 ssot
```

**Gate individual:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 gate INV-TRAIN-XXX
```

**Gate all:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 all
```

**Drift check (dry-run):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 drift
```

**Promote (bulk, só com drift legítimo e gates ok):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inv.ps1 promote
```

---

## EXIT CODES (semântica obrigatória)

| Exit Code | Significado | Ação |
|-----------|-------------|------|
| **0** | PASS | Pode prosseguir |
| **1** | FAIL | Corrigir verifier/pytest; **PROIBIDO "DONE"** |
| **3** | DRIFT ou GOLDEN_MISSING | Revisar mudança e promover golden (somente se VERIFY_EXIT=0 e PYTEST_EXIT=0) |

---

## LOOP OBRIGATÓRIO POR INV

1. Implementar/alterar SPEC/test/validator
2. Rodar: `inv.ps1 gate INV-TRAIN-XXX`
3. **Se EXIT != 0**: corrigir e voltar ao passo (2)
4. **Só então permitir "DONE"**

---

## MUDANÇA DE INFRA (qualquer arquivo abaixo)

- `verify_invariants_tests.py`
- `INVARIANTS_TRAINING.md`
- `scripts/run_invariant_gate*.ps1`
- `scripts/inv.ps1`

**Obrigatório:**
1. `inv.ps1 all`
2. **Se EXIT=3**: `inv.ps1 drift` → revisar → `inv.ps1 promote`
3. `inv.ps1 all` e exigir **EXIT=0**

---

## EVIDÊNCIA OBRIGATÓRIA NO OUTPUT (para revisão humana)

**Mudança 1 INV**: colar "GATE VERDICT" completo (Report + VERIFY_EXIT + PYTEST_EXIT + EXIT_CODE)

**Infra**: colar "GATE ALL SUMMARY" + "AGGREGATED RESULT" + EXIT_ALL

---

## HELPER CANÔNICO PARA TESTES DB

**Testes de invariantes DB runtime (classe A) devem usar helper canônico para asserts de violações Postgres.**

### Localização
```python
from tests._helpers.pg_error import assert_pg_constraint_violation
```

### Contrato (API pública)
```python
assert_pg_constraint_violation(
    exc_info,              # pytest.ExceptionInfo[IntegrityError]
    expected_sqlstate,     # str: "23514" (CHECK) ou "23505" (UNIQUE)
    expected_constraint    # str: nome da constraint
)
```

### Exemplo de Uso
```python
with pytest.raises(IntegrityError) as exc_info:
    await async_db.flush()

# Verifica constraint usando helper canônico (driver-agnostic)
assert_pg_constraint_violation(
    exc_info, "23514", "ck_wellness_post_rpe"
)
```

### Benefícios
- ✅ Driver-agnostic (psycopg2 sync + asyncpg async)
- ✅ Reduz 5 linhas → 1 chamada
- ✅ Elimina acesso direto a `orig.diag` / `orig.__cause__`
- ✅ Centraliza lógica de extração de constraints

**Regra**: PROIBIDO acessar `orig.diag.constraint_name` ou `orig.__cause__.constraint_name` diretamente em testes de invariantes. Usar helper canônico.

---

## ANTI-PATTERNS (PROIBIDO)

❌ Promover golden com VERIFY_EXIT != 0 ou PYTEST_EXIT != 0  
❌ Promover golden sem rodar -WhatIf (drift) primeiro em bulk  
❌ Declarar "DONE" sem evidência (gate output)  
❌ Inventar valores de SPEC/OpenAPI/schema sem verificar SSOT  
❌ Rodar promote esperando bootstrap funcionar quando o discovery do gate_all ainda não inclui golden_missing: YES  
❌ Promover se VERIFY_EXIT != 0 ou PYTEST_EXIT != 0  
❌ **Acessar `orig.diag` ou `orig.__cause__` diretamente em testes DB** (usar helper canônico)
