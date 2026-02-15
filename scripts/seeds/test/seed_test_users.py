# HB_SCRIPT_KIND=SEED
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/seeds/test/seed_test_users.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Seed: Usuários de teste com cada papel

Cria 1 usuário com cada papel para testes (dirigente, coordenador, treinador, atleta, membro).
NOTA: Super admin já existe via migrations.
"""
import sys
from pathlib import Path
import uuid

# Adicionar backend ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from passlib.context import CryptContext
from app.core.db import db_context


# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_test_users():
    """Cria usuários de teste para cada papel."""
    with db_context() as session:
        # Buscar organização IDEC
        result = session.execute(
            text("SELECT id FROM organizations WHERE name = 'IDEC' LIMIT 1")
        )
        org_row = result.fetchone()
        
        if not org_row:
            print("[ERRO] Organização IDEC não encontrada. Execute seed_test_organization primeiro.")
            return
            
        org_id = org_row[0]
        
        # Buscar IDs dos papéis (com maiúscula inicial)
        roles_query = text("""
            SELECT name, id FROM roles 
            WHERE name IN ('Dirigente', 'Coordenador', 'Treinador', 'Atleta', 'Membro')
        """)
        roles_result = session.execute(roles_query)
        roles = {row[0]: row[1] for row in roles_result.fetchall()}
        
        if len(roles) != 5:
            print(f"[ERRO] Nem todos os papéis foram encontrados. Encontrados: {list(roles.keys())}")
            return
        
        # Definir usuários de teste
        test_users = [
            {
                'role': 'Dirigente',
                'email': 'dirigente@idec.com',
                'name': 'João Silva',
                'password': 'Dirigente@123!'
            },
            {
                'role': 'Coordenador', 
                'email': 'coordenador@idec.com',
                'name': 'Maria Santos',
                'password': 'Coordenador@123!'
            },
            {
                'role': 'Treinador',
                'email': 'treinador@idec.com', 
                'name': 'Pedro Costa',
                'password': 'Treinador@123!'
            },
            {
                'role': 'Atleta',
                'email': 'atleta@idec.com',
                'name': 'Ana Oliveira',
                'password': 'Atleta@123!'
            },
            {
                'role': 'Membro',
                'email': 'membro@idec.com',
                'name': 'Carlos Ferreira',
                'password': 'Membro@123!'
            }
        ]
        
        created_count = 0
        
        for user_data in test_users:
            # Verificar se usuário já existe
            check_result = session.execute(
                text("SELECT COUNT(*) FROM users WHERE email = :email"),
                {"email": user_data['email']}
            )
            if check_result.scalar() > 0:
                print(f"[SKIP] Usuário {user_data['email']} já existe")
                continue
                
            # Criar person (separar nome completo em primeiro e último nome)
            person_id = str(uuid.uuid4())
            name_parts = user_data['name'].split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            session.execute(text("""
                INSERT INTO persons (id, full_name, first_name, last_name, created_at, updated_at)
                VALUES (:person_id, :full_name, :first_name, :last_name, NOW(), NOW())
            """), {
                "person_id": person_id,
                "full_name": user_data['name'],
                "first_name": first_name,
                "last_name": last_name
            })
            
            # Hash da senha
            password_hash = pwd_context.hash(user_data['password'])
            
            # Criar user
            user_id = str(uuid.uuid4())
            session.execute(text("""
                INSERT INTO users (id, person_id, email, password_hash, status, created_at, updated_at)
                VALUES (:user_id, :person_id, :email, :password_hash, 'ativo', NOW(), NOW())
            """), {
                "user_id": user_id,
                "person_id": person_id,
                "email": user_data['email'],
                "password_hash": password_hash
            })
            
            # Buscar role_id
            role_id = roles[user_data['role']]
            
            # Criar org_membership
            membership_id = str(uuid.uuid4())
            session.execute(text("""
                INSERT INTO org_memberships (id, person_id, organization_id, role_id, start_at, created_at, updated_at)
                VALUES (:membership_id, :person_id, :org_id, :role_id, NOW(), NOW(), NOW())
            """), {
                "membership_id": membership_id,
                "person_id": person_id,
                "org_id": org_id,
                "role_id": role_id
            })
            
            print(f"[OK] Usuário {user_data['role']} criado: {user_data['email']} / {user_data['password']}")
            created_count += 1
        
        print(f"\n[OK] {created_count} usuários de teste criados para IDEC")


if __name__ == "__main__":
    seed_test_users()
