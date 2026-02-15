# HB Track Custom Agents

This directory contains agent-specific protocol overrides.

## Protocol Inheritance

All agents MUST inherit from:
1. `docs/_canon/AI_KERNEL.md` (LEVEL 0)
2. `docs/_canon/ARCH_REQUEST_GENERATION_PROTOCOL.md` (LEVEL 1)

## Agent Pattern

Create one file per agent role:
- `executor-agent.md`
- `reviewer-agent.md`
- `architect-agent.md`

Each file MUST declare:

```yaml
role: <name>
inherits: [AI_KERNEL.md, ARCH_REQUEST_GENERATION_PROTOCOL.md]
overrides: []
```

## Usage

When invoking an agent:

```
@agent architect-agent
Generate ARCH_REQUEST for X
```

Agent automatically loads its protocol stack from `inherits` chain.

## Status

**Version:** 1.0.0  
**Last Updated:** 2026-02-13
