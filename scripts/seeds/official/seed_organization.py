# HB_SCRIPT_KIND=SEED
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/seeds/official/seed_organization.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Seed: Organização inicial (R34)
Cria o clube único da V1 vinculado ao superadmin
"""
import sys
from pathlib import Path

# Adicionar backend ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.core.db import db_context
import uuid


def seed_organization():
    with db_context() as session:
        # Verificar se já existe organização
        result = session.execute(text("SELECT COUNT(*) FROM organizations"))
        count = result.scalar()

        if count > 0:
            print(f"[SKIP] Organizacao ja existe ({count} organizacao(es)). Pulando seed.")
            return

        # Criar organização (R34 - clube único na V1)
        org_id = uuid.uuid4()
        session.execute(text("""
            INSERT INTO organizations (id, name)
            VALUES (:org_id, 'Clube HB Tracking')
        """), {"org_id": org_id})

        print("[OK] Organizacao criada!")
        print(f"   Nome: Clube HB Tracking")
        print(f"   ID: {org_id}")


if __name__ == "__main__":
    seed_organization()

