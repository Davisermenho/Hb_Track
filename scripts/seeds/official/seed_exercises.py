# HB_SCRIPT_KIND=SEED
# HB_SCRIPT_SCOPE=db
# HB_SCRIPT_SIDE_EFFECTS=DB_WRITE
# HB_SCRIPT_IDEMPOTENT=NO
# HB_SCRIPT_ENTRYPOINT=python scripts/seeds/official/seed_exercises.py
# HB_SCRIPT_OUTPUTS=stdout
"""
Seed canônico para banco de exercícios e tags (Step 19)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.exercise_tag import ExerciseTag
from app.models.exercise import Exercise
from app.models.exercise_favorite import ExerciseFavorite
from app.models.user import User

DATABASE_URL = "postgresql+asyncpg://hbtrack_dev:hbtrack_dev_pwd@localhost:5433/hb_track_dev"

async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        # Busca organização e usuário (ou cria um usuário de teste se necessário)
        from sqlalchemy import text
        from uuid import UUID as parse_uuid
        
        org_result = await session.execute(text("SELECT id, name FROM organizations LIMIT 1"))
        org_row = org_result.fetchone()
        if not org_row:
            print("[ERRO] Nenhuma organização encontrada. Execute os seeds principais primeiro.")
            return
        org_id, org_name = org_row
        
        user_result = await session.execute(text("SELECT id, email FROM users LIMIT 1"))
        user_row = user_result.fetchone()
        if not user_row:
            # Criar usuário de teste para seed de exercícios
            test_user_id = uuid4()
            await session.execute(text("""
                INSERT INTO users (id, email, password_hash, is_active, created_at, updated_at)
                VALUES (:id, :email, :password_hash, true, NOW(), NOW())
            """), {
                'id': test_user_id,
                'email': 'seed_exercises@test.com',
                'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqgdXnGV8W'  # password123
            })
            await session.commit()
            user_id = test_user_id
            user_email = 'seed_exercises@test.com'
            print(f"[INFO] Usuário de teste criado: {user_email}")
        else:
            user_id, user_email = user_row
        
        print(f"[INFO] Usando organização: {org_name} (ID: {org_id})")
        print(f"[INFO] Usando usuário: {user_email} (ID: {user_id})")
        
        # Tags hierárquicas (pais)
        tatico = ExerciseTag(id=uuid4(), name="Tático", description="Aspectos táticos", display_order=1, is_active=True)
        tecnico = ExerciseTag(id=uuid4(), name="Técnico", description="Aspectos técnicos", display_order=2, is_active=True)
        fisico = ExerciseTag(id=uuid4(), name="Físico", description="Aspectos físicos", display_order=3, is_active=True)
        fundamentos = ExerciseTag(id=uuid4(), name="Fundamentos", description="Fundamentos do esporte", display_order=4, is_active=True)
        session.add_all([tatico, tecnico, fisico, fundamentos])
        await session.flush()
        
        # Tags filhas
        tags = [
            ExerciseTag(name="Ataque Posicional", parent_tag_id=tatico.id, is_active=True),
            ExerciseTag(name="Defesa Posicionada", parent_tag_id=tatico.id, is_active=True),
            ExerciseTag(name="Transição Ofensiva", parent_tag_id=tatico.id, is_active=True),
            ExerciseTag(name="Transição Defensiva", parent_tag_id=tatico.id, is_active=True),
            ExerciseTag(name="Contra-Ataque", parent_tag_id=tatico.id, is_active=True),
            ExerciseTag(name="Passe", parent_tag_id=tecnico.id, is_active=True),
            ExerciseTag(name="Drible", parent_tag_id=tecnico.id, is_active=True),
            ExerciseTag(name="Arremesso", parent_tag_id=tecnico.id, is_active=True),
            ExerciseTag(name="Finta", parent_tag_id=tecnico.id, is_active=True),
            ExerciseTag(name="Recepção", parent_tag_id=tecnico.id, is_active=True),
            ExerciseTag(name="Velocidade", parent_tag_id=fisico.id, is_active=True),
            ExerciseTag(name="Resistência", parent_tag_id=fisico.id, is_active=True),
            ExerciseTag(name="Força", parent_tag_id=fisico.id, is_active=True),
            ExerciseTag(name="Agilidade", parent_tag_id=fisico.id, is_active=True),
            ExerciseTag(name="Aquecimento", parent_tag_id=fundamentos.id, is_active=True),
            ExerciseTag(name="Finalização", parent_tag_id=fundamentos.id, is_active=True),
            ExerciseTag(name="Coordenação", parent_tag_id=fundamentos.id, is_active=True),
        ]
        session.add_all(tags)
        await session.flush()
        
        # Exercícios exemplo (com organization_id e created_by_user_id obrigatórios)
        exercises = [
            Exercise(
                name="Ataque 3x3", 
                description="Exercício de ataque posicional 3x3", 
                tag_ids=[str(tags[0].id)],  # Converte UUID para string
                category="Tático", 
                organization_id=org_id,
                created_by_user_id=user_id
            ),
            Exercise(
                name="Defesa 5x5", 
                description="Treino de defesa posicionada", 
                tag_ids=[str(tags[1].id)], 
                category="Tático", 
                organization_id=org_id,
                created_by_user_id=user_id
            ),
            Exercise(
                name="Circuito de Velocidade", 
                description="Exercício físico para velocidade", 
                tag_ids=[str(tags[10].id)], 
                category="Físico", 
                organization_id=org_id,
                created_by_user_id=user_id
            ),
            Exercise(
                name="Aquecimento Dinâmico", 
                description="Aquecimento geral com coordenação", 
                tag_ids=[str(tags[14].id), str(tags[16].id)], 
                category="Fundamentos", 
                organization_id=org_id,
                created_by_user_id=user_id
            ),
        ]
        session.add_all(exercises)
        await session.commit()
        
        print(f"[OK] Criadas {len(tags) + 4} tags de exercícios")
        print(f"[OK] Criados {len(exercises)} exercícios de exemplo")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())

