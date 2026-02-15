---
description: Carregar quando a tarefa envolver criação/execução de EXEC_TASK ou ADR.
applyTo: "docs/execution_tasks/**, docs/ADR/**"
---

# EXEC_TASK and ADR Generation Rules

## When Generating EXEC_TASK

**OBRIGATÓRIO:**
- Load `docs/_canon/EXEC_TASK_GENERATION_PROTOCOL.md` before starting
- Operate in **EXECUTOR MODE**
- Follow procedural format with ordered steps
- Define evidence blocks with exit codes (0/2/3)
- Anchor to SSOT (schema.sql, openapi.json, models)

**Required Sections:**
1. OBJETIVO EXECUTÁVEL (specific, actionable)
2. PRÉ-REQUISITOS (with validation checks)
3. FASES DE EXECUÇÃO (ordered steps with commands)
4. EVIDÊNCIAS (artifacts that prove completion)
5. ROLLBACK (how to undo if needed)

**Forbidden:**
- Redefining architecture (belongs to ARCH_REQUEST)
- Recording "why" decisions (belongs to ADR)
- Vague suggestions without validation criteria

---

## When Generating ADR

**OBRIGATÓRIO:**
- Load `docs/_canon/ADR_GENERATION_PROTOCOL.md` before starting
- Operate in **HISTORIAN MODE**
- Maintain neutral, historical tone
- Use ADR template: `docs/ADR/_TEMPLATE_ADR.md`
- Validate against schema: `docs/_canon/_schemas/adr.schema.json`

**Required Sections:**
1. Header (Status, Date, Autor, Fase, Módulos Afetados)
2. Contexto (why this decision was needed)
3. Decisão (what/how/why - NO commands)
4. Alternativas Consideradas (rejected options with reasoning)
5. Consequências (positive/negative/neutral)
6. Validação (criteria for conformance - NOT execution steps)

**Forbidden:**
- Step-by-step execution (belongs to EXEC_TASK)
- Commands or scripts (belongs to EXEC_TASK)
- TODO lists (belongs to EXEC_TASK)

---

## Role Boundaries

Agents MUST respect role boundaries defined in:
→ `docs/_canon/_agent/AGENT_ROLE_MATRIX.md`

Invalid behaviors:
- Executor creating ADR (should only create EXEC_TASK)
- Historian generating commands (should only record rationale)
- Mixing layers (EXEC_TASK + ADR content in one file)

---

## After Creation

**EXEC_TASK:**
- Update execution_tasks/ folder
- Reference source ARCH_REQUEST (if applicable)
- Define event.json for tracking

**ADR:**
- Update `docs/ADR/_INDEX_ADR.md`
- Assign ADR number (sequential)
- Link to related ARCH_REQUEST/EXEC_TASK

---

## Exit Codes Reference

| Code | Meaning | Use Case |
|------|---------|----------|
| 0 | PASS | All criteria met |
| 2 | Structural diff | Parity violation, schema mismatch |
| 3 | Guard violation | Protected file modified without authorization |
| 4 | Requirements violation | Model/business rule violation |

---

Status: Canonical Instruction
Version: 1.0.0
Last Updated: 2026-02-13
