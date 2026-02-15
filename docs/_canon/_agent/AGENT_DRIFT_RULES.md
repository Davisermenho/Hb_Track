# Agent Drift Rules — HB Track

Defines operational criteria for detecting and remediating agent drift.

Agent drift = deviation from canonical protocols and role boundaries.

---

## 1. Definition

**Agent Drift** occurs when:

1. Output format deviates from canonical structure
2. Language shifts from deterministic to conversational
3. Role boundaries are violated
4. Protocols are ignored or misapplied

Drift is a quality degradation signal requiring remediation.

---

## 2. Structural Drift

### 2.1 JSON where Markdown expected

**Rule:** Artifacts MUST be Markdown, not JSON.

**Violation Examples:**
```json
{
  "arch_request": {
    "title": "Add wellness table",
    "objectives": ["Create table"]
  }
}
```

**Correct:**
```markdown
# ARCH_REQUEST — Add wellness table

## OBJETIVOS (MUST)
- Table MUST exist in schema.sql
```

**Detection:** Regex pattern `^\s*{` in .md files

---

### 2.2 Mixed Layers in Single Artifact

**Rule:** One artifact = one layer only.

**Violation Examples:**
- ARCH_REQUEST containing execution commands
- EXEC_TASK redefining architectural requirements
- ADR containing step-by-step implementation

**Detection:** 
- Search for "ARCH_REQUEST" + "EXEC_TASK" in same file
- Search for commands (`powershell`, `python`, `git`) in ARCH_REQUEST
- Search for RFC 2119 keywords (`MUST`, `SHALL`) in EXEC_TASK decision sections

**Threshold:** 1 occurrence = WARNING; 3+ = BLOCKER

---

### 2.3 Missing Required Sections

**Rule:** Artifacts MUST contain all required sections per protocol.

**ARCH_REQUEST Required:**
- Header (Status, Task ID, Priority)
- CONTEXTO
- OBJETIVOS (MUST)
- SSOT & AUTORIDADE
- GATES

**EXEC_TASK Required:**
- Header (Status, Estimativa)
- OBJETIVO EXECUTÁVEL
- PRÉ-REQUISITOS
- FASES DE EXECUÇÃO

**ADR Required:**
- Header (Status, Date)
- Contexto
- Decisão
- Consequências

**Detection:** Section heading regex per protocol

**Threshold:** 1 missing = BLOCKER

---

## 3. Language Drift

### 3.1 Conversational Tone

**Rule:** Artifacts MUST be formal, not conversational.

**Forbidden Phrases:**
- `acho que` / `I think`
- `podemos` / `we can`
- `na minha opinião` / `in my opinion`
- `seria legal` / `it would be nice`
- `talvez` / `maybe`
- `recomendo` / `I recommend`

**Correct Alternatives:**
- `MUST` / `SHALL` (normative)
- `The system requires` (factual)
- `Evidence shows` (analytical)

**Detection:** Regex patterns (case-insensitive)

**Threshold:** 1-2 = WARNING; 3+ = BLOCKER

---

### 3.2 Hedging Language

**Rule:** Normative sections MUST use RFC 2119 keywords only.

**Forbidden in OBJETIVOS/Gates:**
- `deveria` / `should consider`
- `pode ser que` / `might`
- `é possível` / `it's possible`
- `provavelmente` / `probably`

**Required:**
- `MUST`, `MUST NOT`
- `SHALL`, `SHALL NOT`
- `REQUIRED`, `FORBIDDEN`

**Detection:** Absence of RFC 2119 in normative sections

**Threshold:** 1 hedge in critical section = BLOCKER

---

### 3.3 Promotional Language

**Rule:** Technical docs MUST be neutral.

**Forbidden:**
- `melhor solução` / `best solution`
- `ideal` / `ideal`
- `perfeito` / `perfect`
- `recomendado` / `recommended` (except in protocol context)

**Correct:**
- `canonical solution`
- `deterministic approach`
- `validated pattern`

**Detection:** Keyword search

**Threshold:** 1-3 = WARNING; 4+ = BLOCKER

---

## 4. Protocol Drift

### 4.1 Execution in Architecture Artifacts

**Rule:** ARCH_REQUEST MUST NOT contain executable commands.

**Violation Examples:**
```markdown
## EXECUTION PLAN
powershell.exe -Command "alembic upgrade head"
```

**Detection:** 
- Commands in ARCH_REQUEST: `powershell`, `python`, `bash`, `cmd`
- Code blocks with execution syntax

**Threshold:** 1 occurrence = BLOCKER

---

### 4.2 Architecture in Execution Artifacts

**Rule:** EXEC_TASK MUST NOT redefine architecture.

**Violation Examples:**
```markdown
## PHASE 1
First, we need to reconsider the table schema...
MUST add new column `priority` to wellness_pre
```

**Detection:**
- Architectural RFC 2119 in execution phases
- Phrases: `reconsider`, `redefine`, `change architecture`

**Threshold:** 1 occurrence = BLOCKER

---

### 4.3 Implementation in Decision Artifacts

**Rule:** ADR MUST NOT contain code or commands.

**Violation Examples:**
```markdown
## Decisão
Run the following migration:
```sql
ALTER TABLE wellness_pre ADD COLUMN status TEXT;
```
```

**Detection:**
- Code blocks in ADR (except for illustrative schema examples)
- Commands in "Decisão" or "Consequências" sections

**Threshold:** Implementation commands = BLOCKER; illustrative code = OK

---

### 4.4 Role Boundary Violations

**Rule:** Agents MUST respect role matrix.

**Violation Examples:**
- Architect generating EXEC_TASK (should only generate ARCH_REQUEST)
- Executor creating ADR (should only generate EXEC_TASK)
- Reviewer modifying code (should only report issues)

**Detection:**
- Cross-role artifact generation
- Missing "MODO: <ROLE>" declaration before role-specific tasks

**Threshold:** 1 violation = BLOCKER

---

## 5. Detection Thresholds

| Drift Type | Severity | WARNING Threshold | BLOCKER Threshold |
|-----------|---------|-------------------|-------------------|
| JSON in Markdown | High | N/A | 1 occurrence |
| Mixed layers | High | 1 instance | 3+ instances |
| Missing sections | Critical | N/A | 1 section |
| Conversational tone | Medium | 1-2 phrases | 3+ phrases |
| Hedging language | High | N/A | 1 in normative section |
| Promotional language | Low | 1-3 words | 4+ words |
| Execution in ARCH | Critical | N/A | 1 command |
| Architecture in EXEC | Critical | N/A | 1 redefinition |
| Implementation in ADR | High | N/A | 1 command |
| Role violation | Critical | N/A | 1 violation |

**Exit Codes:**
- 0 = No drift detected
- 1 = Warnings (non-blocking, informational)
- 2 = Blockers (CI MUST fail, human review required)

---

## 6. Remediation

### 6.1 Structural Drift

**Action:** Rewrite artifact in correct format.

**Example:**
- JSON → Markdown conversion
- Split mixed-layer artifacts into separate files
- Add missing sections with placeholder content

---

### 6.2 Language Drift

**Action:** Replace conversational/hedging with normative language.

**Tool:** `docs/scripts/_ia/validators/prompt_sanitizer.py`

**Example:**
```bash
# Before
"Acho que podemos criar a tabela wellness_pre"

# After (sanitized)
"Table wellness_pre MUST be created in schema"
```

---

### 6.3 Protocol Drift

**Action:** Move content to correct artifact type.

**Example:**
- Commands in ARCH_REQUEST → Create new EXEC_TASK
- Architecture changes in EXEC_TASK → Update ARCH_REQUEST first
- Implementation in ADR → Extract to EXEC_TASK, keep rationale only

---

### 6.4 Role Drift

**Action:** Reroute to correct role.

**Example:**
```
# Violation detected
Architect attempted to generate EXEC_TASK

# Remediation
1. Architect completes ARCH_REQUEST
2. Hand off to Executor
3. Executor generates EXEC_TASK
```

---

## 7. Detection Automation

### 7.1 Manual Detection

**When:** Ad-hoc artifact review

**Tool:** Human inspection using this document as checklist

---

### 7.2 Automated Detection

**When:** CI/CD pipeline, pre-commit hooks

**Tool:** `docs/scripts/_ia/validators/agent_drift_detector.py`

**Invocation:**
```bash
python docs/scripts/_ia/validators/agent_drift_detector.py
```

**Output:**
```
[DRIFT] JSON detected in docs/_canon/ARCH_REQUEST_example.md
[DRIFT] Layer mixing in docs/execution_tasks/EXEC_TASK_001.md
[DRIFT] Conversational tone in docs/ADR/ADR-042.md
[OK] docs/ADR/ADR-043.md compliant
```

---

### 7.3 Continuous Monitoring

**When:** Weekly governance audits

**Tool:** CI workflow (non-blocking)

**Config:** `.github/workflows/quality-gates.yml`

---

## 8. Governance Integration

### 8.1 Referenced By

- `AI_KERNEL.md` (LEVEL 0 constitution)
- `AGENT_ROLE_MATRIX.md` (role enforcement)
- `ai_governance_linter.py` (validation orchestration)

---

### 8.2 Enforced By

- `agent_drift_detector.py` (automated detection)
- Human reviewers (manual inspection)
- CI workflows (blocking on BLOCKER drift)

---

## Status
**Canonical — Agent Quality Assurance**

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** LEVEL 1 (governance rules)

## Related Documents
- `AGENT_ROLE_MATRIX.md` (role boundaries)
- `LANGUAGE_PROTOCOL.md` (RFC 2119 rules)
- `FAILSAFE_PROTOCOL.md` (block-on-ambiguity)
