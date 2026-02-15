# GUARDRAIL_POLICY_PARITY.md

> **Parent:** [`GUARDRAILS_INDEX.md`](GUARDRAILS_INDEX.md) (Entry point único para todos os guardrails)  
> **Domain:** Parity Policy (schema.sql ↔ SQLAlchemy models)  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13

## Descrição
Guardrail para parity validation: quando divergência entre schema.sql e models é aceitável vs quando é bloqueante.

---

## Política: Schema.sql é SSOT

### Declaração
Verdade sobre a estrutura do banco é **schema.sql** (gerado por `inv.ps1 refresh`, SSOT).

Model Python deve ser um reflexo **exato** de schema.sql (estruturalmente):
- Tabelas, colunas, tipos, constraints (PK/FK/UNIQUE/CHECK)
- Defaults, nullability
- Indices, comments (opcional, mas recomendado)

### Aceitável Drift
Estes diffs entre schema.sql e models são **OK**:
- Docstrings/comments em models (schema.sql não tem essas)
- Type hints em Python (not in DDL)
- Relacionamentos SQLAlchemy (não no DDL, mas em model.py)
- Validadores Pydantic (não no DDL, mas em model.py)

### Não-Aceitável Drift (Blocking)
Estes diffs são **ERROS** e devem ser bloqueados (exit=2):
- Coluna em schema.sql faltando em model.py
- Tipo de coluna divergente (VARCHAR vs INTEGER)
- Constraint faltando (PK, FK, UNIQUE, CHECK)
- Coluna em model.py não em schema.sql
- Nullability divergente

---

## Validação: Parity Gate

**Comando:**
```powershell
parity_gate.ps1 -Table <T>
```

**Saída Esperada:**
- Exit=0: Parity perfeita (estruturalmente em acordo)
- Exit=2: Parity violation (diff encontrado)

**Se Exit=2:**
1. Ler `parity_report.json` e encontrar exatamente qual coluna/constraint difere
2. Opções:
   a) Editar model.py (se schema.sql está correto)
   b) Editar schema.sql + Alembic migration (se schema incorreto)
   c) Rodar `models_autogen_gate.ps1` para regenerar model.py
3. Rerun parity até exit=0

---

## Checklist: Parity Validation

- [ ] `inv.ps1 refresh` executado (schema.sql atualizado)
- [ ] `parity_gate.ps1` retornou exit=0
- [ ] `parity_report.json` tem zero DIFFs
- [ ] Model.py não foi reescrito (revisado manualmente)
- [ ] Nenhuma coluna foi dropada acidentalmente

---

## Recovery Paths

### Cenário 1: Parity exit=2 persistente
```
1. Abrir parity_report.json
2. Identificar DIFFs específicos (linhas, tipos de coluna)
3. Se schema.sql correto → editar model.py específico
4. Se model.py correto → schema.sql pode estar desatualizado (inv.ps1 refresh?)
5. Rerun parity
```

### Cenário 2: Autogen reescreveu model.py
```
1. git diff --name-only (ver qual arquivo mudou)
2. git restore <arquivo> (opcional, se quiser versão anterior)
3. Revisar mudanças (git diff) → se OK, git add
4. Rerun parity para confirmar sincronia
```

### Cenário 3: Schema.sql desatualizado
```
1. Rodar inv.ps1 refresh (repo root, COM APROVAÇÃO)
2. git diff docs/_generated/schema.sql (revisar mudanças)
3. Rerun parity com schema novo
```

---

## TODO
- [ ] Criar script de diff viewer (lado a lado: schema.sql vs models)
- [ ] Documentar quando (se nunca) é aceitável editar manualmente model.py
- [ ] Adicionar alerting para parity violations crônicas
