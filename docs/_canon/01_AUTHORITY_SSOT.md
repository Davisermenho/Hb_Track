# Autoridade & SSOT (Single Source of Truth)

## Ordem de Precedência

Quando há discrepância, responda nesta ordem:

1. **DB Constraints** (`schema.sql` - CHECK, UNIQUE, FK, NOT NULL, DEFAULT)
2. **Service Validations** (código em `app/models/`, `app/services/`)
3. **OpenAPI Contracts** (`openapi.json` - schemas, operationIds, parâmetros)
4. **Documentação Manual** (ADRs, guides, INVARIANTS)

---

## SSOT vs Derivado vs Fila

| Categoria | Exemplos | Uso |
|-----------|----------|-----|
| **SSOT** (Confie sem dúvida) | `schema.sql`, `INVARIANTS_TRAINING.md`, ADRs | Referência final; atualizar aqui |
| **Derivado** (Gerado a partir de SSOT) | `alembic_state.txt`, `parity_report.json`, `*_report.*` | Verificar alinhamento; regenerar se divergir |
| **Fila** (Candidatos, não vinculante) | `training_invariants_backlog.md`, `training_invariants_candidates.md` | Planejamento; não use para validar |

---

## Fonte Normativa

**ADR Referência:** [001-ADR-TRAIN-ssot-precedencia.md](../ADR/001-ADR-TRAIN-ssot-precedencia.md)

Qualquer debate sobre precedência resolve-se consultando este ADR.

---

## Exemplo de Aplicação

**Cenário:** Há divergência entre `schema.sql` e `app/models/User.py` sobre `email` UNIQUE.

1. Verificar `schema.sql` → SSOT; se lá diz UNIQUE, é verdade
2. Corrigir `app/models/User.py` para refletir
3. Gerar novo alembic migration
4. Validar parity_report.json pós-migração
5. Documentar decisão em ADR
