# Copilot Handshake Template

## Agent: HB Track AI Agent
**Role:** Code Quality Validator
**Version:** 1.0.0

---

## Handshake Protocol

### Step 1: ACK (Acknowledgment)
Agent must acknowledge understanding of:
- SSOT sources: `docs/_canon/00_START_HERE.md`
- Exit codes: `docs/references/exit_codes.md`
- Approved commands: `docs/_canon/08_APPROVED_COMMANDS.md`

**Response format:**
```
ACK: I have read and understood the canonical documentation.
SSOT: docs/_generated/schema.sql, docs/_generated/openapi.json
Exit codes: 0 (pass), 1 (crash), 2 (parity), 3 (guard), 4 (requirements)
```

### Step 2: ASK (Clarification)
If agent needs clarification, use this format:
```
ASK: [Specific question about task scope/constraints]
CONTEXT: [Relevant file/line/command]
REASON: [Why clarification is needed]
```

### Step 3: EXECUTE (Proceed)
Only proceed after ACK confirmed.

---

## TODO
- Add spec-specific handshake rules
- Document retry policy for failed ACKs
