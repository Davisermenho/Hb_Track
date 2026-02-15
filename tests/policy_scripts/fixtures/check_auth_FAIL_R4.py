#!/usr/bin/env python3
# HB_SCRIPT_KIND: RUNNER  # ❌ ERRADO (path sugere CHECK)
# HB_SCRIPT_SCOPE: auth
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: tests/policy_scripts/fixtures/check_auth_FAIL_R4.py
# HB_SCRIPT_OUTPUTS: stdout

"""
Sentinela 6: FAIL - Kind/Path mismatch (R4.2)

Este script tem KIND=RUNNER mas o nome sugere CHECK.
Esperado: FAIL (exit 2) com código HB005 (KIND_MISMATCH)
"""

def validate_auth():
    """Validação de autenticação (exemplo)."""
    pass

if __name__ == "__main__":
    validate_auth()
    print("Auth validation complete")
