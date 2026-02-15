#!/usr/bin/env python3
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SCOPE: testing
# HB_SCRIPT_SIDE_EFFECTS: NONE
# HB_SCRIPT_IDEMPOTENT: true
# HB_SCRIPT_ENTRYPOINT: tests/policy_scripts/fixtures/check_tests_FAIL_R7.py
# HB_SCRIPT_OUTPUTS: stdout

"""
Sentinela 3: FAIL - Check com pytest (forbidden invoke)

Este script VIOLA R7: checks NÃO podem invocar pytest.
Esperado: FAIL (exit 2) com código CHECKS-E_FORBIDDEN_INVOKE
"""

import subprocess

def run_tests():
    # ❌ FORBIDDEN: checks não podem executar pytest
    subprocess.run(["pytest", "tests/"])

if __name__ == "__main__":
    run_tests()
    print("Tests completed")
