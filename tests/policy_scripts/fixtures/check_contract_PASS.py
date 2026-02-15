#!/usr/bin/env python3
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: openapi
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: tests/policy_scripts/fixtures/check_contract_PASS.py
# HB_SCRIPT_OUTPUTS: stdout

"""
Sentinela 1: PASS - Check correto e read-only

Validador de contrato OpenAPI (read-only, sem side-effects).
Esperado: PASS (exit 0)
"""

import json
from pathlib import Path

def validate():
    """Função de validação read-only (exemplo)."""
    # Exemplo de leitura sem side-effects
    schema_path = Path("docs/_generated/openapi.json")
    if schema_path.exists():
        with open(schema_path) as f:
            data = json.load(f)
        return True
    return False

if __name__ == "__main__":
    validate()
    print("PASS: Contract validation complete")
