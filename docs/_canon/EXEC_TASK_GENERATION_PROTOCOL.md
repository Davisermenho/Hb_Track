# EXEC_TASK Generation Protocol

## Purpose
Define how AI agents MUST generate EXEC_TASK artifacts
in HB Track with deterministic execution semantics.

This protocol governs execution-layer artifacts.

---

## 1. Role

Agents operating under this protocol are:

**EXECUTOR MODE**

They MUST:
- Translate ARCH_REQUEST into execution steps
- Produce reproducible procedures
- Emit verifiable evidence requirements

---

## 2. Layer Separation

| Layer | Artifact |
|------|---------|
| Architecture | ARCH_REQUEST |
| Execution | EXEC_TASK |
| Governance | ADR |

Agents MUST NOT mix layers.

---

## 3. Mandatory Properties

EXEC_TASK MUST:

- Be procedural
- Contain ordered steps
- Include commands when applicable
- Define evidence blocks
- Be executable by humans or agents

EXEC_TASK MUST NOT:

- Redefine architecture
- Introduce new requirements
- Modify ARCH_REQUEST intent

---

## 4. Determinism

Two identical inputs MUST generate:

- Same step ordering
- Same validation criteria
- Same evidence structure

Execution ambiguity is forbidden.

---

## 5. Evidence Contract

Each EXEC_TASK MUST define:

- Expected outputs
- Exit codes (when applicable)
- Validation artifacts
- Idempotency rules

Example:

- Exit 0 = PASS
- Exit 2 = Parity diff
- Exit 3 = Guard violation

---

## 6. SSOT Usage

EXEC_TASK MUST anchor to:

- schema.sql
- openapi.json
- Models
- Canonical scripts

No speculative commands.

---

## 7. Failure Rules

If execution cannot be determined:

Agents MUST return:

BLOCKED: Insufficient SSOT for execution plan

---

## 8. Output Rules

Valid EXEC_TASK output:

✔ Steps  
✔ Commands  
✔ Evidence  

Invalid:

❌ Architecture discussion  
❌ Opinions  
❌ Roadmaps  

---

## 9. Template Structure (Normative)

Every EXEC_TASK MUST contain:

### Header (Required)
```markdown
# EXEC_TASK — <TITLE>

Status: DRAFT | IN_PROGRESS | BLOCKED | COMPLETED
Priority: HIGH | MEDIUM | LOW
Estimativa: <hours>h
Assignee: <who>
Related ARCH_REQUEST: <AR-ID> (if applicable)
```

### Body Sections

1. **🎯 OBJETIVO EXECUTÁVEL** — Specific, actionable goal
2. **📋 PRÉ-REQUISITOS** — Prerequisites with validation checks
3. **🔄 FASES DE EXECUÇÃO** — Ordered execution phases
4. **📊 EVIDÊNCIAS** — What artifacts prove completion
5. **🔒 ROLLBACK** — How to undo if needed

Each phase MUST include:
- Step-by-step commands
- Expected outputs
- Exit code meanings
- Validation criteria

---

## 10. Prohibited Content

EXEC_TASK MUST NOT contain:

- Architectural decisions (belongs to ARCH_REQUEST)
- Rationale for "why" (belongs to ADR)
- Vague suggestions ("consider doing...")
- Unverifiable success criteria

---

## Status
**Canonical — Execution Layer Binding**

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** LEVEL 1 Protocol (extends AI_KERNEL.md)

## Related Protocols
- `ARCH_REQUEST_GENERATION_PROTOCOL.md` (sibling — architecture layer)
- `ADR_GENERATION_PROTOCOL.md` (sibling — decision layer)
- `LANGUAGE_PROTOCOL.md` (parent — RFC 2119 rules)
