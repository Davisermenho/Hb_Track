# WHEN_TO_USE_TASK_BRIEF.md

> **Status:** CANONICAL  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13  
> **Applies To:** AI Architect (decision-making guide)
>
> **Parent:** [`GOVERNANCE_MODEL.md`](../GOVERNANCE_MODEL.md) (hierarquia normativa)  
> **Related:** [`AI_ARCH_EXEC_PROTOCOL.md`](AI_ARCH_EXEC_PROTOCOL.md) (operational protocol), [`TASK_BRIEF.md`](TASK_BRIEF.md) (template), [`AI_PROTOCOL_CHECKLIST.md`](AI_PROTOCOL_CHECKLIST.md) (pre-validation)

---

## 🎯 Propósito

Este documento estabelece **critérios objetivos e mensuráveis** para decidir quando escalar uma tarefa de:
- **Prompt Operacional** (execução direta via agent) → **TASK BRIEF Formal** (protocolo completo com 6 fases)

**Princípio fundamental:** Maximizar eficiência em tarefas simples; minimizar risco em tarefas complexas.

---

## 🚦 Decision Framework (5 Critérios Obrigatórios)

Avaliar **TODOS** os 5 critérios abaixo. Se **QUALQUER** critério indicar "TASK BRIEF Required", escalar para protocolo formal.

### Critério 1: Scope (Arquivos Afetados)

| Condition | Threshold | Decision |
|-----------|-----------|----------|
| Leitura/modificação de arquivos | ≤ 2 files | ✅ Direct execution OK |
| Leitura/modificação de arquivos | 3-5 files | ⚠️ Consider TASK BRIEF (evaluate outros critérios) |
| Leitura/modificação de arquivos | > 5 files | 🔴 TASK BRIEF **obrigatório** |

**Exceção:** Batch operations em files homogêneos (ex: 40 models SQLAlchemy) com mesmo workflow → pode usar direct execution SE aprovado em [08_APPROVED_COMMANDS.md](../../_canon/08_APPROVED_COMMANDS.md).

---

### Critério 2: SSOT Impact (Single Source of Truth)

| Condition | Examples | Decision |
|-----------|----------|----------|
| **SSOT modification** | `schema.sql`, `openapi.json`, `alembic_state.txt`, `manifest.json`, ADRs | 🔴 TASK BRIEF **obrigatório** |
| **SSOT-dependent code** | SQLAlchemy models (depende schema.sql), API routes (depende openapi.json) | ⚠️ Consider TASK BRIEF (se > 2 models/routes) |
| **Não afeta SSOT** | Docstrings, comments, logs, tests (não-estruturais) | ✅ Direct execution OK |

**Regra:** Mudanças em SSOT = mudanças arquiteturais = TASK BRIEF obrigatório.

---

### Critério 3: Estimativa de Tempo

| Condition | Threshold | Decision |
|-----------|-----------|----------|
| Tarefa simples (< 5 comandos) | < 10 min | ✅ Direct execution OK |
| Tarefa média (5-10 comandos) | 10-30 min | ⚠️ Consider TASK BRIEF (evaluate exit codes + risk) |
| Tarefa complexa (> 10 comandos) | > 30 min | 🔴 TASK BRIEF **obrigatório** |

**Heurística:** Se precisa de > 2 checkpoints intermediários (validações entre passos) → TASK BRIEF.

---

### Critério 4: Complexity Score (Gates + Commands)

| Condition | Examples | Decision |
|-----------|----------|----------|
| **Single gate/command** | `parity_scan.ps1 -Table X`, `model_requirements.py --table Y` | ✅ Direct execution OK |
| **Composed gate (atomic)** | `models_autogen_gate.ps1` (PRE parity + autogen + POST parity + requirements) | ⚠️ Atomic composition OK SE aprovado em 08_APPROVED_COMMANDS.md |
| **Multiple sequential gates** | Parity → fix manual → requirements → guard → baseline snapshot | 🔴 TASK BRIEF **obrigatório** (muitos pontos de falha) |
| **Conditional branching** | IF exit=2 THEN X ELSE IF exit=4 THEN Y ELSE Z | 🔴 TASK BRIEF **obrigatório** (não-determinístico sem plan) |

**Regra:** Mais de 1 gate sequencial OU branching condicional → TASK BRIEF obrigatório.

---

### Critério 5: Risk Level (Impact + Reversibility)

| Condition | Examples | Decision |
|-----------|-----------|----------|
| **HIGH RISK (irreversível)** | `git reset --hard`, `git clean -fd`, `dropdb`, `DELETE FROM` (sem WHERE) | 🔴 TASK BRIEF **obrigatório** + explicit authorization |
| **MEDIUM RISK (parcialmente reversível)** | Editar models (reversível via git), criar migration (reversível via downgrade) | ⚠️ TASK BRIEF recomendado se > 2 models |
| **LOW RISK (totalmente reversível)** | `git status`, read-only queries, `parity_scan.ps1 -TableFilter` (read-only) | ✅ Direct execution OK |

**Regra:** Qualquer operação que afete dados em produção ou quebre histórico Git → TASK BRIEF obrigatório.

---

## 📊 Decision Matrix (Combinação de Critérios)

| Files | SSOT | Time | Gates | Risk | Decision |
|-------|------|------|-------|------|----------|
| ≤2 | No | <10m | 1 | Low | ✅ **Direct** |
| 3-5 | No | 10-30m | 1-2 | Low-Med | ⚠️ **Consider** (agent discretion) |
| >5 | - | - | - | - | 🔴 **TASK BRIEF** |
| - | Yes | - | - | - | 🔴 **TASK BRIEF** |
| - | - | >30m | - | - | 🔴 **TASK BRIEF** |
| - | - | - | >2 | - | 🔴 **TASK BRIEF** |
| - | - | - | - | High | 🔴 **TASK BRIEF** (+ explicit auth) |

**Nota:** Uma fila única de 🔴 = TASK BRIEF obrigatório (critério suficiente).

---

## 💡 Exemplos Práticos (Casos Reais)

### ✅ Direct Execution (OK)

**Caso 1: Diagnóstico read-only**
```
Tarefa: "Rodar parity scan na tabela attendance"
- Files: 0 (read-only)
- SSOT: No (não modifica)
- Time: < 5 min
- Gates: 1 (parity_scan.ps1)
- Risk: Low (read-only)
→ DECISION: Direct execution OK
```

**Caso 2: Correção de typo**
```
Tarefa: "Corrigir typo no docstring de athlete.py linha 42"
- Files: 1
- SSOT: No (docstring não é SSOT)
- Time: < 2 min
- Gates: 0
- Risk: Low (docstring)
→ DECISION: Direct execution OK
```

**Caso 3: Single model fix (simple)**
```
Tarefa: "Adicionar validator faltando em attendance.athlete_id"
- Files: 1 (attendance.py)
- SSOT: No (model respeita schema.sql existente)
- Time: 10 min
- Gates: 1 (requirements)
- Risk: Medium (reversível via git)
→ DECISION: Direct execution OK (SE < 5 linhas + single validator)
```

---

### 🔴 TASK BRIEF Required (Obrigatório)

**Caso 4: Multiple models com parity fix**
```
Tarefa: "Corrigir parity em 4 models: athlete, attendance, person, team"
- Files: 4 (> 3 threshold)
- SSOT: No direto, mas models dependem schema.sql
- Time: 40 min
- Gates: 4 (parity per table)
- Risk: Medium (4 reversões se erro)
→ DECISION: TASK BRIEF obrigatório (Critério 1: >3 files)
```

**Caso 5: SSOT change (schema.sql)**
```
Tarefa: "Adicionar coluna 'status' em training_sessions table"
- Files: 2 (migration + model)
- SSOT: YES (schema.sql mudará)
- Time: 20 min
- Gates: 2 (alembic upgrade + parity)
- Risk: Medium (migration irreversível se pushado)
→ DECISION: TASK BRIEF obrigatório (Critério 2: SSOT impact)
```

**Caso 6: Complex workflow (conditional branching)**
```
Tarefa: "Implementar INV-TRAIN-042 com gate + promote se drift"
- Files: 3 (SPEC, test, validator)
- SSOT: No
- Time: 45 min
- Gates: 3 (verify + pytest + drift check) + conditional (IF drift THEN promote)
- Risk: Medium (golden file modification)
→ DECISION: TASK BRIEF obrigatório (Critério 3: >30min + Critério 4: conditional branching)
```

**Caso 7: Architectural decision (ADR-level change)**
```
Tarefa: "Consolidar 5 arquivos de guardrails em index único"
- Files: 6 (5 updates + 1 new)
- SSOT: No, mas architectural change
- Time: 60 min
- Gates: 0 (documentação)
- Risk: Medium (backward compatibility concern)
→ DECISION: TASK BRIEF obrigatório (Critério 1: >5 files + Critério 3: >30min)
```

---

## 🔄 Escalation Workflow (Flowchart)

```
┌─────────────────────────────────┐
│ User Request Received           │
└──────────┬──────────────────────┘
           │
           ├─ Evaluate Criterion 1 (Files): > 5? ────────→ YES → 🔴 TASK BRIEF
           │                                              ↓ NO
           ├─ Evaluate Criterion 2 (SSOT): Impacted? ────→ YES → 🔴 TASK BRIEF
           │                                              ↓ NO
           ├─ Evaluate Criterion 3 (Time): > 30min? ─────→ YES → 🔴 TASK BRIEF
           │                                              ↓ NO
           ├─ Evaluate Criterion 4 (Gates): > 2 seq? ────→ YES → 🔴 TASK BRIEF
           │                                              ↓ NO
           ├─ Evaluate Criterion 5 (Risk): High? ────────→ YES → 🔴 TASK BRIEF + Auth
           │                                              ↓ NO
           └─ ALL criteria LOW → ✅ Direct Execution
                                    │
                                    ├─ Execute with single prompt
                                    ├─ Capture output + exit code
                                    └─ Report result
```

---

## 📝 TASK BRIEF Creation Checklist

Se decisão = 🔴 TASK BRIEF obrigatório, seguir este checklist:

1. **Pre-Validation (AI_PROTOCOL_CHECKLIST.md)**
   - [ ] 10 sections validated
   - [ ] Determinism Score ≥ 4
   - [ ] SSOT identified and referenced

2. **TASK BRIEF Structure (TASK_BRIEF.md template)**
   - [ ] Section 1: Task Overview (ID, Title, Version, Priority, Budget)
   - [ ] Section 2: Context & SSOT (Problem, Goal, Authority)
   - [ ] Section 3: Scope (Read/Write allowlist, Prohibited paths)
   - [ ] Section 4: Execution Plan (Step-by-step with preflight + verification)
   - [ ] Section 5: Acceptance Criteria (Binary yes/no checks)
   - [ ] Section 6: Stop Conditions (Critical failures → abort)
   - [ ] Section 7: Rollback Plan (Recovery commands)
   - [ ] Section 8: Architect Authorization (Checklist validated declaration)

3. **Execution Protocol (AI_ARCH_EXEC_PROTOCOL.md 6 phases)**
   - [ ] Phase 1: Context Harvesting (consultar docs/_canon/)
   - [ ] Phase 2: Pre-Validation (checklist + determinism score)
   - [ ] Phase 3: TASK BRIEF emission (template completo)
   - [ ] Phase 4: Delivery to Executor (monitor drift)
   - [ ] Phase 5: Evidence Audit (EVIDENCE_PACK validation)
   - [ ] Phase 6: Finalization (CHANGELOG + EXECUTIONLOG + ADR se necessário)

4. **Post-Execution Validation**
   - [ ] EVIDENCE_PACK received (command log, artifacts, gate outputs, exit codes)
   - [ ] Acceptance Criteria all PASS
   - [ ] Repo clean (`git status --porcelain` expected state)
   - [ ] CHANGELOG/EXECUTIONLOG updated

---

## 🚫 Anti-Patterns (PROIBIDO)

❌ **Executar TASK BRIEF para tarefas triviais**: "Corrigir typo" não precisa de 6-phase protocol (burocracia excessiva)  
❌ **Executar Direct para mudanças SSOT**: "Adicionar coluna" sem TASK BRIEF = alto risco de drift  
❌ **Bypassar Determinism Score**: Se Score < 4, refinar demanda antes de emitir TASK BRIEF  
❌ **Assumir reversibilidade sem validar**: `git reset --hard` não é reversível (TASK BRIEF + Auth obrigatório)  
❌ **Criar TASK BRIEF "retroativo"**: Se tarefa já começou via direct execution, TASK BRIEF não aplica (documentar em EXECUTIONLOG como ad-hoc)

---

## 📊 Métricas de Compliance

**Objetivo:** 90% de tarefas classificadas corretamente (Direct vs TASK BRIEF)

**Tracking:**
- **False Positives** (TASK BRIEF desnecessário): Count de TASK BRIEFs emitidos para tarefas < 3 files + < 10 min + 0 SSOT impact
- **False Negatives** (TASK BRIEF omitido quando necessário): Count de ADR-required changes ou SSOT changes executados sem TASK BRIEF
- **Escalation Time**: Tempo médio de decisão (should be < 2 min após evaluate 5 critérios)

**Audit:** Consultar [`EXECUTIONLOG.md`](../../execution_tasks/EXECUTIONLOG.md) para histórico de decisões (Task IDs com TASK BRIEF vs direct execution).

---

## 🔗 Documentação Relacionada

**LEVEL 0 (GOVERNANCE):**
- [`GOVERNANCE_MODEL.md`](../GOVERNANCE_MODEL.md) — Hierarquia normativa (precedência)
- [`AI_ARCH_EXEC_PROTOCOL.md`](AI_ARCH_EXEC_PROTOCOL.md) — Protocolo operacional completo (6 fases)
- [`AI_PROTOCOL_CHECKLIST.md`](AI_PROTOCOL_CHECKLIST.md) — Pre-validation (10 sections, Determinism Score)
- [`TASK_BRIEF.md`](TASK_BRIEF.md) — Template formal (8 sections)
- [`EVIDENCE_PACK.md`](EVIDENCE_PACK.md) — Template de output (execution report)

**LEVEL 1 (CANONICAL):**
- [`00_START_HERE.md`](../../_canon/00_START_HERE.md) — Porta única de navegação
- [`08_APPROVED_COMMANDS.md`](../../_canon/08_APPROVED_COMMANDS.md) — Comando whitelist (atomic compositions aprovados)

**LEVEL 2 (OPERATIONAL):**
- [`GUARDRAILS_INDEX.md`](../../_ai/_guardrails/GUARDRAILS_INDEX.md) — Entry point para guardrails (baseline, parity, requirements)

---

## 🛠️ Troubleshooting

**Sintoma:** "Tarefa parece simples mas tem 5 critérios conflitantes"  
**Ação:** Priorizar critério mais restritivo (qualquer 🔴 = TASK BRIEF obrigatório)

**Sintoma:** "Determinism Score = 3 após checklist"  
**Ação:** Refinar demanda com user (clarify scope, SSOT, acceptance criteria) até Score ≥ 4

**Sintoma:** "TASK BRIEF emitido mas Executor saiu do escopo (agent drift)"  
**Ação:** Interromper execução, corrigir Section 3 (Scope allowlist mais restritivo), re-emitir TASK BRIEF

**Sintoma:** "Direct execution falhou 2x com mesmo erro"  
**Ação:** Escalar para TASK BRIEF retroativamente (documentar em EXECUTIONLOG como "escalated after 2 failures")

**Sintoma:** "Não sei se batch de 40 models é 'direct' ou 'TASK BRIEF'"  
**Ação:** Se batch command aprovado em `08_APPROVED_COMMANDS.md` (ex: `models_batch.ps1`) → direct OK; caso contrário → TASK BRIEF

---

## 📅 Histórico de Mudanças

| Version | Date | Change | Impact |
|---------|------|--------|--------|
| 1.0.0 | 2026-02-13 | Criação do WHEN_TO_USE_TASK_BRIEF.md (R4 remediation) | Clear escalation criteria; eliminated ambiguity of "when to use formal protocol" |

---

## 📝 Notas de Auditoria

**Governance Audit:** [GOVERNANCE_AUDIT_REPORT.md](GOVERNANCE_AUDIT_REPORT.md)  
**Audit Finding:** R4 — Coverage Gap (no bridge document explaining when to escalate from operational prompts to formal TASK BRIEF)  
**Resolution:** Created WHEN_TO_USE_TASK_BRIEF.md with 5 objective criteria (Files, SSOT, Time, Gates, Risk) + decision matrix + practical examples  
**Impact:** Clear decision framework; reduced ambiguity (90% target for correct classification); prevented bureaucracy overhead for trivial tasks; ensured risk mitigation for complex tasks

**Task ID:** T-556 (R4 — Bridge Document)  
**Branch:** `docs/gov-unify-001`  
**Validation:** 5 criteria evaluated in < 2 min; 7 practical examples (3 direct, 4 TASK BRIEF); flowchart for escalation workflow
