# ADR Generation Protocol

## Purpose
Define how agents MUST generate Architecture Decision Records (ADR)
within HB Track governance.

ADR documents record WHY decisions exist.

---

## 1. Role

ADR Mode = **DECISION HISTORIAN**

Agents MUST:
- Capture rationale
- Preserve context
- Avoid execution detail

---

## 2. ADR Scope

ADR MUST include:

- Context (why this decision was needed)
- Decision (what was decided)
- Consequences (implications of the decision)
- Alternatives (optional — what was considered but rejected)

ADR MUST NOT include:

- Step-by-step execution
- Commands
- Implementation details

---

## 3. Layer Integrity

ADR sits above:

- EXEC_TASK (execution)
- Implementation (code)

But below:

- AI_KERNEL (constitution)
- Governance model (meta-rules)

---

## 4. Tone

ADR MUST be:

- Neutral
- Historical
- Analytical

ADR MUST NOT be:

- Prescriptive
- Operational
- Conversational

---

## 5. Determinism

Given the same decision context:

ADR outputs MUST preserve:
- Semantic meaning
- Structure
- Decision clarity

Non-deterministic phrasing is forbidden.

---

## 6. Prohibited Content

ADR MUST NOT contain:

- TODO lists
- Execution steps
- Migration instructions
- Commands or scripts

These belong to EXEC_TASK.

---

## 7. Failure Handling

If rationale is missing:

Agents MUST return:

BLOCKED: Decision rationale unavailable

Do not guess or invent rationale.

---

## 8. Template Structure (Normative)

Every ADR MUST follow this structure:

### Header (Required)
```markdown
# ADR-<NUMBER> — <TITLE>

**Status:** PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED
**Date:** YYYY-MM-DD
**Autor:** <name>
**Fase:** <project phase>
**Módulos Afetados:** <list>
```

### Body Sections

1. **Contexto** — Problem description + references (PRD, issues, etc.)
2. **Decisão** — What/How/Why + technical details (NO commands)
3. **Alternativas Consideradas** — Rejected options with reasoning
4. **Consequências** — Positive/Negative/Neutral impacts
5. **Validação** — Criteria for conformance (NOT execution steps)

---

## 9. Reference Template

Agents MUST use:

→ `docs/ADR/_TEMPLATE_ADR.md`

As the authoritative template.

---

## 10. Schema Validation

ADRs MUST validate against:

→ `docs/_canon/_schemas/adr.schema.json`

Required fields:
- title
- status
- date
- context
- decision
- consequences

---

## 11. Index Maintenance

After creating ADR:

Agents MUST update:

→ `docs/ADR/_INDEX_ADR.md`

With ADR number, title, summary.

---

## Status
**Canonical — Governance Layer Binding**

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** LEVEL 1 Protocol (extends AI_KERNEL.md)

## Related Protocols
- `ARCH_REQUEST_GENERATION_PROTOCOL.md` (sibling — architecture layer)
- `EXEC_TASK_GENERATION_PROTOCOL.md` (sibling — execution layer)
- `LANGUAGE_PROTOCOL.md` (parent — RFC 2119 rules)
