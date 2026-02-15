# GUARDRAIL_POLICY_REQUIREMENTS.md

> **Parent:** [`GUARDRAILS_INDEX.md`](GUARDRAILS_INDEX.md) (Entry point único para todos os guardrails)  
> **Domain:** Requirements Policy (profiles: strict/fk/lenient)  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13

## Descrição
Guardrail para requirements validation: quais validações são obrigatórias (strict), quais são permissivas, recovery paths.

---

## Política: Profiles Determinam Severidade

### Profiles
1. **strict** (default): Sem warnings, sem violations
   - Ciclos FK → bloqueado
   - Validadores faltando → erro
   - Defaults faltando → erro
   - Qualquer warning → erro

2. **fk** (apenas ciclos FK conhecidos): Permite ciclos de FK
   - Ciclos FK → permitido (com `-AllowCycleWarning`)
   - Outras validações → como strict

3. **lenient** (debug/experimento): Apenas erros críticos
   - Warnings → ignorado
   - Ciclos FK → permitido
   - Validadores → leniência

### Quando Usar Qual Profile

| Tabela | Reason | Profile | Flags |
|--------|--------|---------|-------|
| Maioria | Normal, sem FK ciclos | strict | — |
| `teams`, `seasons` | Cicl FK (team→season←team pattern) | fk | -AllowCycleWarning |
| Experimental/Debug | Prototipagem rápida | lenient | (nenhum) |

---

## Validação: Requirements Gate

**Comando:**
```powershell
model_requirements.py --table <T> --profile strict
```

**Saída Esperada:**
- Exit=0: Todos requirements passados
- Exit=4: Requirements violation (erro encontrado)

**Se Exit=4:**
1. Ler output e encontrar linha específica (line number + erro)
2. Abrir model.py (app/models/<module>.py)
3. Encontrar a linha e corrigir:
   - Adicionar validador faltando
   - Adicionar default faltando
   - Ajustar tipo/constraint
4. Rerun requirements até exit=0

---

## Aceitável vs Não-Aceitável

### Aceitável (exit=0)
- Model sem docstrings (não validado)
- Relationship sem doc (não validado)
- Comment divergente com schema (não validado)
- Type hints ausentes (opcional)

### Não-Aceitável (exit=4)
- Validator Django/Pydantic faltando (se obrigatório)
- Default divergente (e.g., schema says DEFAULT='active' mas model não tem)
- Nullability divergente (schema NULL mas model NOT_NULL em validator)
- Constraint faltando (CHECK, UNIQUE divergente)

---

## Checklist: Requirements Validation

- [ ] Coretto profile escolhido (strict vs fk vs lenient)
- [ ] `model_requirements.py` retornou exit=0
- [ ] Nenhum warning apareceu (se profile=strict)
- [ ] Se profile=fk: `-AllowCycleWarning` foi usado
- [ ] Output revisado antes de prosseguir (no surprises)

---

## Recovery Paths

### Cenário 1: Exit=4 (violation encontrado)
```
1. Parser o output para encontrar "Line X: <erro>"
2. Abrir app/models/<module>.py linha X
3. Identificar qual validador/default/constraint falta
4. Adicionar/corrigir
5. Rerun requirements
```

### Cenário 2: Ciclo FK em tabela strict
```
Problem: Model não passa com profile=strict (ciclo FK detectado)

Opções:
a) Mudar para profile=fk se ciclo é intencional
b) Renomear constraints para quebrar ciclo (if não intencional)
c) Investigar schema.sql para confirmar ciclo (maybe Alembic error)

Ação:
1. Confirmar ciclo é intencional
2. Rodar com -Profile fk -AllowCycleWarning
3. Documentar em ADR se novo padrão
```

### Cenário 3: Validator genérico demais
```
Problem: Validator muito lenient, deixa dados inválidos passar

Solução:
1. Refinar validator (mais específico)
2. Adicionar test case que reprova o valor inválido
3. Rerun requirements + test suite
```

---

## TODO
- [ ] Criar catálogo de validators obrigatórios por tipo/coluna
- [ ] Documentar como criar custom validators
- [ ] Adicionar alerting para requirements violations recorrentes
