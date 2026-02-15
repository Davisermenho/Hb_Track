#!/usr/bin/env python3
"""
generate-handshake-template.py

Purpose: Generate handshake-templates.md from agent-spec.json
Input: docs/_ai/_specs/SPEC_AGENT_*.json
Output: .github/copilot-handshake.md
"""

import json
import sys
from pathlib import Path


def generate_template(spec: dict) -> str:
    """Generate handshake template from spec."""
    template = f"""# Copilot Handshake Template

## Agent: {spec.get('agent', {}).get('name', 'Unknown')}
**Role:** {spec.get('agent', {}).get('role', 'N/A')}
**Version:** {spec.get('version', '1.0.0')}

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
"""
    return template


def main():
    """Main generation logic."""
    # Generate generic template (TODO: parse actual spec files)
    spec = {
        "agent": {"name": "HB Track AI Agent", "role": "Code Quality Validator"},
        "version": "1.0.0"
    }
    
    template = generate_template(spec)
    
    output_path = Path(".github/copilot-handshake.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template, encoding='utf-8')
    
    print(f"✅ Generated handshake template: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
