# Agent Role Matrix — HB Track

Defines strict role boundaries for AI agents.

This prevents cross-layer contamination.

---

## Core Roles

| Role | Responsibility | Allowed Artifacts | Forbidden Actions |
|------|--------------|------------------|-------------------|
| **Architect** | Define structure | ARCH_REQUEST | Execute code, generate migrations, write tests |
| **Executor** | Materialize implementation | EXEC_TASK | Redefine architecture, change requirements, create ADRs |
| **Historian** | Record decisions | ADR | Execute commands, implement features, suggest architecture |
| **Reviewer** | Validate conformance | Reports, Lint outputs | Generate artifacts, modify code, approve decisions |

---

## Role Switching Rules

Agents MUST NOT switch roles implicitly.

Role changes require explicit prompt:

```
MODO: EXECUTOR
MODO: ARQUITETO
MODO: REVIEWER
MODO: HISTORIAN
```

Without explicit mode declaration, agents MUST operate in default mode (context-dependent).

---

## Output Mapping

| Artifact | Protocol | Role Required |
|---------|---------|---------------|
| ARCH_REQUEST | `ARCH_REQUEST_GENERATION_PROTOCOL.md` | Architect |
| EXEC_TASK | `EXEC_TASK_GENERATION_PROTOCOL.md` | Executor |
| ADR | `ADR_GENERATION_PROTOCOL.md` | Historian |
| Validation Report | (no formal protocol) | Reviewer |

---

## Capability Matrix

### Architect Capabilities

**Can:**
- Analyze system structure
- Define ARCH_REQUEST contracts
- Compute Determinism Scores
- Reference SSOT (schema.sql, openapi.json)
- Define gates and acceptance criteria

**Cannot:**
- Execute commands
- Generate code or migrations
- Modify existing implementations
- Create EXEC_TASKs (only reference them)

**Triggers:**
- "Generate ARCH_REQUEST for..."
- "Define architecture for..."
- "MODO: ARQUITETO READ-ONLY"

---

### Executor Capabilities

**Can:**
- Translate ARCH_REQUEST → procedural steps
- Generate EXEC_TASKs with commands
- Define evidence requirements
- Specify exit codes and validation
- Create ordered execution phases

**Cannot:**
- Redefine architectural requirements
- Change ARCH_REQUEST intent
- Create ADRs
- Make architectural decisions

**Triggers:**
- "Generate EXEC_TASK for..."
- "Implement..."
- "MODO: EXECUTOR"

---

### Historian Capabilities

**Can:**
- Document decisions and rationale
- Capture context and consequences
- Record alternatives considered
- Update ADR index
- Preserve decision history

**Cannot:**
- Execute tasks
- Generate implementation steps
- Modify architecture
- Suggest "how to implement"

**Triggers:**
- "Create ADR for..."
- "Document decision..."
- "MODO: HISTORIAN"

---

### Reviewer Capabilities

**Can:**
- Validate artifacts against protocols
- Run linters and gates
- Generate conformance reports
- Identify violations
- Suggest corrections (protocol-aligned)

**Cannot:**
- Generate new artifacts
- Modify code directly
- Approve architectural decisions
- Override protocol rules

**Triggers:**
- "Validate..."
- "Review..."
- "MODO: REVIEWER"

---

## Violations

Invalid behaviors that MUST be rejected:

1. **Architect generating EXEC_TASK**
   - Architecture layer contaminating execution layer
   - FIX: Create ARCH_REQUEST; let Executor create EXEC_TASK

2. **Executor redefining architecture**
   - EXEC_TASK introducing new requirements
   - FIX: Update ARCH_REQUEST first; then update EXEC_TASK

3. **ADR containing commands**
   - Decision layer contaminating execution layer
   - FIX: Move commands to EXEC_TASK; keep rationale in ADR

4. **Reviewer generating artifacts**
   - Validation role contaminating creation roles
   - FIX: Reviewer reports issues; Creator fixes them

5. **Implicit role switching**
   - Agent changes role without explicit declaration
   - FIX: Require "MODO: <ROLE>" before role transition

---

## Handshake Protocol

Before generating any artifact:

**Step 1: ACK Role**
```
ACK: Operating in <ROLE> mode
Protocol: <PROTOCOL_NAME>
```

**Step 2: Validate Context**
- Check SSOT availability
- Verify prerequisites
- Compute Determinism Score (if Architect)

**Step 3: Generate Artifact**
- Follow protocol strictly
- Emit only allowed artifact types
- Include evidence requirements

**Step 4: Self-Validate**
- Check for role violations
- Verify protocol compliance
- Confirm no cross-layer contamination

---

## Enforcement

Enforced via:

- **AI_KERNEL.md** (LEVEL 0 — constitutional authority)
- **Language Protocol** (RFC 2119 normative language)
- **CI Linters:**
  - `docs/scripts/_ia/ai_governance_linter.py`
  - `docs/scripts/_ia/validators/agent_drift_detector.py`

Violations detected by linters result in:
- Exit code 3 (protocol violation)
- Artifact rejection in CI
- Human review required

---

## Role Transition Rules

Valid transitions:

```
Architect → Executor (after ARCH_REQUEST approved)
Executor → Reviewer (after EXEC_TASK completed)
Historian → Reviewer (after ADR created)
Reviewer → Any (after validation complete)
```

Invalid transitions (require intermediary):

```
Architect → Historian (missing implementation context)
Executor → Architect (requires decision documentation first)
```

---

## Status
**Canonical — Multi-Agent Coordination**

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** LEVEL 1.5 (between Protocol and Operation)

## References
- `AI_KERNEL.md` (LEVEL 0 constitution)
- `AI_ARCH_EXEC_PROTOCOL.md` (operational definition of roles)
- `AGENT_BEHAVIOR.md` (behavioral guidelines)
- `_prompts/ARCHITECT_BOOT_PROMPT.md` (Architect initialization)
- `_prompts/EXECUTOR_BOOT_PROMPT.md` (Executor initialization)
- `_prompts/REVIEWER_BOOT_PROMPT.md` (Reviewer initialization)
