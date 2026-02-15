# scripts/diagnostics

Read-only human triage (not CI).

- **MUST** be read-only (DB_READ, FS_READ, NONE)
- **MAY** be verbose (more context for manual inspection)
- Outputs go to `scripts/artifacts/diagnostics/`

See `scripts/_policy/templates/diagnostics/README.md` for template reference.
