# docs/scripts/_ia/

## AI Infrastructure for HB Track Backend

This directory contains **extractors**, **validators**, **generators**, and **agents** for automating AI documentation, quality gates, and infrastructure validation.

### Directory Structure

```
docs/scripts/_ia/
├── extractors/          # Extract SSOT → YML/JSON for AI consumption
├── validators/          # Validate docs/code against schemas
├── generators/          # Generate AI artifacts from SSOT
├── utils/               # Shared utilities (YAML/JSON loaders, git parsers)
└── requirements.txt     # Python dependencies (radon, lizard, pyyaml, jsonschema)
```

### Extractors (6 tools)

- **extract-ai-context.py** — Extract SSOT from 00_START_HERE.md → AI_CONTEXT.md
- **extract-quality-gates.py** — Convert QUALITY_METRICS.md → quality-gates.yml
- **extract-workflows.py** — Extract workflows from 03_WORKFLOWS.md → workflows.yml
- **extract-adr-index.py** — Generate adr-index.json from ADR metadata
- **extract-approved-commands.py** — Convert 08_APPROVED_COMMANDS.md → approved-commands.yml
- **extract-troubleshooting.py** — Convert 09_TROUBLESHOOTING_GUARD_PARITY.md → troubleshooting-map.json

### Validators (5 tools)

- **validate-ai-docs-sync.py** — Validate docs/_ai ↔ docs/_canon sync (for CI)
- **validate-quality-gates.py** — Enforce quality gates with radon/lizard
- **validate-agent-spec.py** — Validate agent-spec.json against JSON Schema
- **validate-approved-commands.py** — Check scripts against whitelist
- **validate-yaml-json.py** — Generic YAML/JSON linter with schema validation

### Generators (4 tools)

- **generate-handshake-template.py** — Create handshake-templates.md from agent-spec.json
- **generate-invocation-examples.py** — Generate invocation-examples.yml from EXEC_TASK_*.md
- **generate-checklist-yml.py** — Convert CHECKLIST-CANONICA-MODELS.md → checklist-models.yml
- **generate-ai-index.py** — Auto-regenerate docs/_ai/_INDEX.md

### Agents

- This directory is optional and currently not present in this repo snapshot.
- If reintroduced, agent scripts must be documented and wired into CI explicitly.

### Governance Linters (3 tools)

- **ai_governance_linter.py** — Unified governance validator for ARCH_REQUEST, EXEC_TASK, ADR protocols
- **validators/agent_drift_detector.py** — Detects governance drift (JSON leakage, mixed layers, conversational tone)
- **validators/prompt_sanitizer.py** — Transforms loose prompts into deterministic prompts

**Exit codes:**
- **ai_governance_linter.py**: 0 = OK, 2 = structural, 3 = protocol, 4 = missing canon files
- **agent_drift_detector.py**: 0 = no drift, 1 = warnings (non-blocking), 2 = blockers (must fix)

### Utilities (4 modules)

- **yaml_loader.py** — YAML loader with error handling
- **json_loader.py** — JSON loader with error handling
- **file_reader.py** — UTF-8 file reader with encoding detection
- **git_diff_parser.py** — Parse git diff/numstat metrics

### Installation

```powershell
cd docs/scripts/_ia
pip install -r requirements.txt
```

### Usage

**Validators** are invoked by GitHub Actions CI/CD workflows:

```powershell
python docs/scripts/_ia/validators/validate-ai-docs-sync.py --strict
python docs/scripts/_ia/validators/validate-quality-gates.py --profile strict
```

**Extractors** regenerate SSOT artifacts:

```powershell
python docs/scripts/_ia/extractors/extract-ai-context.py --output docs/_ai/AI_CONTEXT.md
python docs/scripts/_ia/extractors/extract-quality-gates.py --output docs/_ai/quality-gates.yml
```

**Generators** auto-create templates for agents:

```powershell
python docs/scripts/_ia/generators/generate-ai-index.py --output docs/_ai/_INDEX.md
```

**Optional agents** (if directory exists) run autonomously (via cron or GitHub Actions):

```powershell
python docs/scripts/_ia/agents/code-review-agent.py --workspace C:\HB TRACK
python docs/scripts/_ia/agents/parity-check-agent.py --strict
```

### Exit Codes

- **0** — Success
- **1** — Error (crash, invalid file)
- **2** — Validation warning (schema violation, but recoverable)
- **3** — Sync mismatch (docs/_ai and docs/_canon out of sync)

---

**Author:** HB Track Agent Infrastructure  
**Version:** 1.0.0  
**Repository:** https://github.com/HB-Track/backend
