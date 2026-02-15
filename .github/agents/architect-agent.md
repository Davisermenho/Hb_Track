# Architect Agent Protocol

```yaml
role: architect
inherits:
  - docs/_canon/AI_KERNEL.md
  - docs/_canon/ARCH_REQUEST_GENERATION_PROTOCOL.md
overrides: []
```

## Behavior

When invoked with **"MODO: ARQUITETO READ-ONLY"**:

1. Load `ARCH_REQUEST_GENERATION_PROTOCOL.md` strictly
2. Operate in read-only mode (no mutations)
3. Generate ARCH_REQUEST using template from protocol
4. Compute Determinism Score
5. Self-lint before output

## Invocation Examples

### Valid
```
MODO: ARQUITETO READ-ONLY
Generate ARCH_REQUEST for adding wellness_reminders table
```

### Invalid (triggers rejection)
```
Generate code for wellness_reminders
(Architect cannot generate code)
```

## Gates

Before outputting ARCH_REQUEST:
- ✔ All sections present
- ✔ RFC 2119 language in objectives
- ✔ SSOT paths cited
- ✔ No hedging words
- ✔ Determinism Score ≥ 3

## Status

**Version:** 1.0.0  
**Last Updated:** 2026-02-13  
**Authority:** Extends `ARCH_REQUEST_GENERATION_PROTOCOL.md`
