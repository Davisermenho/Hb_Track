#!/usr/bin/env python3
"""
Sentinela 5: FAIL - Script sem header (R1.3)

Este arquivo está em fixtures/ mas simula um script "perdido"
em categoria operacional SEM header HB_SCRIPT_KIND.

Esperado: FAIL (exit 2) com código POLICY-E_UNTAGGED_SCRIPT
"""

def some_function():
    """Função exemplo sem header de script."""
    pass

if __name__ == "__main__":
    some_function()
    print("Orphan script executed")
