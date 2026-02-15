# HB_SCRIPT_KIND=SEED
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/seeds/test/seed_test_organization.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Seed: Organização de teste

Cria uma organização padrão para testes e desenvolvimento.
NOTA: Dados de configuração (roles, permissions, positions) já estão nas migrations.
"""
import sys
from pathlib import Path
import uuid

# Adicionar backend ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.core.db import db_context


def seed_test_organization():
    """Cria organização de teste para desenvolvimento."""
    with db_context() as session:
        # Verificar se já existe organização de teste
        result = session.execute(
            text("SELECT COUNT(*) FROM organizations WHERE name = 'IDEC'")
        )
        count = result.scalar()

        if count > 0:
            print("[SKIP] Organização IDEC já existe. Pulando seed.")
            return

        # Inserir organização IDEC
        org_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO organizations (id, name, created_at, updated_at)
            VALUES (
                :org_id,
                'IDEC',
                NOW(),
                NOW()
            )
        """), {"org_id": org_id})

        print(f"[OK] Organização IDEC criada com ID: {org_id}")
        
        # Verificar se já existe uma temporada 2026
        result = session.execute(
            text("SELECT COUNT(*) FROM seasons WHERE name = 'Temporada 2026'")
        )
        season_count = result.scalar()

        if season_count > 0:
            print("[SKIP] Temporada 2026 já existe.")
            return
        
        # Buscar ou criar um time padrão para associar à temporada
        # (seasons requer team_id, não organization_id)
        result = session.execute(
            text("SELECT id FROM teams LIMIT 1")
        )
        team_row = result.fetchone()
        
        if not team_row:
            # Buscar categoria Juvenil para o time
            result = session.execute(
                text("SELECT id FROM categories WHERE name = 'Juvenil' LIMIT 1")
            )
            category_row = result.fetchone()
            
            if not category_row:
                print("[ERRO] Categoria Juvenil não encontrada para criar time.")
                return
                
            category_id = category_row[0]
            
            # Criar um time padrão se não existir
            team_id = str(uuid.uuid4())
            session.execute(text("""
                INSERT INTO teams (id, name, organization_id, category_id, gender, is_our_team, created_at, updated_at)
                VALUES (
                    :team_id,
                    'Time de Teste',
                    :org_id,
                    :category_id,
                    'feminino',
                    true,
                    NOW(),
                    NOW()
                )
            """), {"team_id": team_id, "org_id": org_id, "category_id": category_id})
            print(f"[OK] Time de teste criado com ID: {team_id}")
        else:
            team_id = team_row[0]
        
        # Criar temporada 2026
        season_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO seasons (id, team_id, name, year, start_date, end_date, created_at, updated_at)
            VALUES (
                :season_id,
                :team_id,
                'Temporada 2026',
                2026,
                '2026-01-01',
                '2026-12-31',
                NOW(),
                NOW()
            )
        """), {"season_id": season_id, "team_id": team_id})

        print(f"[OK] Temporada 2026 criada com ID: {season_id}")


if __name__ == "__main__":
    seed_test_organization()
