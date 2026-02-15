# ARCH_REQUEST Generation Protocol (Read-Only Mode)

## Purpose
Define how AI agents MUST generate ARCH_REQUEST documents
without breaking HB Track architectural determinism.

This protocol applies to:
- ChatGPT
- Copilot
- Claude
- Any repo agent

---

## 1. Operating Mode

Agents MUST operate in:

**ARCHITECT — READ ONLY**

This means:
- No repository mutations
- No execution suggestions
- No implicit implementation planning

ARCH_REQUEST is a contract, not an action plan.

---

## 2. Role Separation (Hard Rule)

| Artifact | Responsibility |
|---------|--------------|
| ARCH_REQUEST | Architecture (what must exist) |
| EXEC_TASK | Execution (how to implement) |
| ADR | Decisions (why) |

Agents MUST NOT mix layers.

---

## 3. Mandatory Constraints

When generating an ARCH_REQUEST, agents MUST:

- Use RFC 2119 language (MUST, MUST NOT, SHALL)
- Produce Markdown DSL (not JSON)
- Remain deterministic and reproducible
- Avoid speculative implementation

Agents MUST NOT:

- Generate migrations
- Suggest code
- Propose file diffs
- Include operational steps

---

## 4. SSOT Usage

Agents MUST rely only on declared SSOT.

Valid SSOT examples:
- docs/_generated/schema.sql
- openapi.json
- Existing SQLAlchemy models
- Canonical docs in docs/_canon/

If SSOT is missing:
Agents MUST declare:

> UNKNOWN (insufficient SSOT)

Instead of guessing.

---

## 5. Read-Only Behavior

In read-only mode agents:

✔ Analyze  
✔ Structure  
✔ Formalize  

They MUST NOT:

❌ Invent tables  
❌ Assume endpoints  
❌ Predict repo state  

No hallucinated architecture.

---

## 6. Language Protocol

ARCH_REQUEST MUST:

- Be Markdown
- Follow HB Track DSL
- Use numbered sections
- Contain explicit gates

ARCH_REQUEST MUST NOT:

- Contain opinions
- Contain recommendations
- Contain conversational tone

This is a contract artifact.

---

## 7. Determinism Rules

Two runs with identical inputs MUST produce:

- Structurally equivalent ARCH_REQUESTs
- Same section ordering
- Same normative language

Non-deterministic phrasing is a violation.

---

## 8. Failure Handling

If constraints cannot be satisfied:

Agents MUST stop and return:

BLOCKED: Missing SSOT or template

They MUST NOT improvise.

---

## 9. Output Contract

Valid output =

✔ ARCH_REQUEST only  
✔ No EXEC_TASK  
✔ No appendix with ideas  
✔ No "next steps" section  

Anything beyond the contract is invalid.

---

## 10. Enforcement

This protocol is enforced by:

- Lint: docs/scripts/_ia/lint_arch_request.py
- Governance: AI_KERNEL.md
- CI: arch-request-protocol-validation.yml

Violations will fail validation.

---

## 11. Example Invocation (for agents)

When prompted:

"MODO: ARQUITETO READ-ONLY"

Agents MUST automatically apply this protocol.

---

## 12. Template Completo (Normativo)

Every ARCH_REQUEST MUST contain the following sections in this exact order:

### Header (Required)
```markdown
# ARCH_REQUEST — <TITLE>

Status: DRAFT | APPROVED_FOR_EXECUTION | BLOCKED | COMPLETED
Version: <semver>
Task ID: AR-YYYY-MM-DD-<SLUG>
Priority: HIGH | MEDIUM | LOW
Budget: MAX_COMMANDS=N / MAX_TIME=Nmin
Determinism Score: [0-5]
```

### Body Sections

1. **CONTEXTO / PROBLEMA** — What architectural gap exists
2. **OBJETIVOS (MUST)** — Normative language only (MUST/SHALL)
3. **SSOT & AUTORIDADE** — Exact SSOT paths (schema.sql, openapi.json, models)
4. **SCOPE (ALLOWLIST)** — Explicit read/write/forbidden paths
5. **DELTA ESTRUTURAL** — Before/After state (no code, only structure)
6. **EXECUTION PLAN** — High-level phases (not bash commands)
7. **GATES DE ACEITAÇÃO** — Binary pass/fail criteria
8. **ACCEPTANCE CRITERIA (BINARY)** — What must be true when done
9. **STOP CONDITIONS** — When to abort (missing SSOT, ambiguity)
10. **ROLLBACK PLAN** — How to undo (git revert, restore baseline)
11. **TEST PLAN** — What tests MUST exist (not how to write them)
12. **ARCHITECT AUTHORIZATION** — Signature block

### Optional Sections

- **RISKS** — Known architectural risks
- **DEPENDENCIES** — Other ARs or ADRs required first
- **NOTES** — Non-normative context

### Section Rules

- Each section MUST use `##` heading level
- Objectives MUST contain at least 3 MUST/SHALL statements
- SSOT section MUST list exact file paths
- Gates MUST be verifiable with exit code 0/non-0

---

## 13. Determinism Score Algorithm

Agents MUST compute Determinism Score (0-5) based on:

| Score | Criteria |
|-------|----------|
| 5 | All SSOT paths exist + all objectives unambiguous + all gates automatable |
| 4 | All SSOT paths exist + objectives clear + gates mostly automatable |
| 3 | SSOT paths exist but incomplete + some ambiguity |
| 2 | Missing SSOT + significant ambiguity |
| 1 | Mostly speculative + no clear SSOT |
| 0 | Hallucinated architecture + no SSOT |

If score < 3: Agent MUST request clarification before generating AR.

---

## 14. Generation Workflow (Mandatory)

When asked to generate an ARCH_REQUEST:

**Step 1: Load SSOT**
- Read docs/_generated/schema.sql
- Read docs/_generated/openapi.json
- Read relevant models in app/models/

**Step 2: Validate Intent**
- Can objectives be stated in RFC 2119 language?
- Are there concrete SSOT references?
- Is this architectural (not operational)?

**Step 3: Compute Determinism Score**
- Apply algorithm from §13
- If < 3: STOP and request clarification

**Step 4: Generate AR**
- Use template from §12
- Fill all required sections
- Cite exact SSOT paths

**Step 5: Self-Lint**
- Check for hedging words (examples include: uncertain modifiers, opinion markers)
- Check for Windows paths (C:\)
- Check for missing sections

**Step 6: Output**
- Return ARCH_REQUEST only
- No explanations
- No "next steps"

---

## Status
**Canonical — Binding**

This file is part of HB Track AI Constitution.

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** LEVEL 1 Protocol (extends AI_KERNEL.md)
