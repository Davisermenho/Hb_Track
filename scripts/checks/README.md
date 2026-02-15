# scripts/checks

Deterministic gates (BCP14).

- **MUST** be read-only (DB_READ, FS_READ, NONE)
- **MUST** return exit codes: 0 (PASS), 2 (FAIL), 3 (HARNESS ERROR)
- Outputs (if any) go to `scripts/artifacts/checks/`

See `scripts/_policy/templates/checks/README.md` for template reference.
