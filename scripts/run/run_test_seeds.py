# HB_SCRIPT_KIND=RUNNER
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=YES
# HB_SCRIPT_ENTRYPOINT=python scripts/run/run_test_seeds.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Executa todos os seeds de teste para desenvolvimento.

NOTA: Este script executa apenas dados de TESTE.
Dados de configuração (roles, permissions, positions) já estão nas migrations.

Seeds executados:
1. Organização IDEC + Temporada 2026
2. Usuários de teste (1 por papel)

Uso: python run_test_seeds.py
"""
import sys
from pathlib import Path

# Adicionar backend ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from seed_test_organization import seed_test_organization
from seed_test_users import seed_test_users


def run_all_test_seeds():
    """Executa todos os seeds de teste em ordem."""
    print("=" * 60)
    print("EXECUTANDO SEEDS DE TESTE")
    print("=" * 60)
    print()
    
    print("NOTA: Dados de configuração (roles, permissions, positions)")
    print("      já estão aplicados via migrations.")
    print()
    
    try:
        # Seed 1: Organização IDEC + Temporada 2026
        print("[1/2] Organização IDEC...")
        seed_test_organization()
        print()
        
        # Seed 2: Usuários de teste
        print("[2/2] Usuários de teste...")
        seed_test_users()
        print()
        
        print("=" * 60)
        print("[OK] TODOS OS SEEDS DE TESTE EXECUTADOS COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERRO] ERRO ao executar seeds: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_all_test_seeds()
