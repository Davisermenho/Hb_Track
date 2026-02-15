"""
Testes funcionais para Refresh Token Persistence & Rotation (Fase 2).
Valida:
1. Rotação de Refresh Token (Login -> Refresh -> New Token).
2. Detecção de Reuso (Reuse Detection -> Kill Switch).
3. Logout (Revogação de Refresh Token).
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.person import Person
from app.models.organization import Organization
from app.models.membership import OrgMembership
from app.models.role import Role
from app.core.security import hash_token, hash_password
from app.main import app
from app.core.db import get_async_db

@pytest_asyncio.fixture()
async def async_client(async_db):
    """
    Cria um cliente assíncrono para testes que compartilha a mesma sessão do banco.
    """
    async def _get_async_db():
        yield async_db
    
    app.dependency_overrides[get_async_db] = _get_async_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.pop(get_async_db, None)


@pytest_asyncio.fixture()
async def test_user(async_db):
    """Cria um usuário com vínculo para testes."""
    import uuid
    from datetime import date
    
    # 1. Organizacao
    oid = uuid.uuid4()
    org = Organization(id=oid, name=f"Test Org {oid.hex[:6]}")
    async_db.add(org)
    
    # 2. Pessoa
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        full_name="Test User",
        first_name="Test",
        last_name="User",
        created_at=datetime.now(timezone.utc)
    )
    async_db.add(person)
    await async_db.flush()
    
    # 3. Usuario (NOT superadmin due to unique constraint)
    uid = uuid.uuid4()
    password = "password123"
    user = User(
        id=uid,
        email=f"test_{uid.hex[:8]}@example.com",
        password_hash=hash_password(password),
        person_id=pid,
        is_superadmin=False,
        status="ativo",
        created_at=datetime.now(timezone.utc)
    )
    async_db.add(user)
    
    # 4. Role e Membership (R42)
    stmt = select(Role).where(Role.code == "treinador")
    res = await async_db.execute(stmt)
    role = res.scalar_one_or_none()
    if not role:
        # Fallback se não houver seed de roles - usar ID que não conflite (uuid ou int alto)
        # Se o banco usar auto-increment int para Role, id=4 pode conflitar se ja houver 1,2,3
        # Mas em muitos casos é fixo. Vou tentar id=999 para evitar conflitos se for o caso.
        role = Role(id=999, name="Treinador", code="treinador")
        async_db.add(role)
        await async_db.flush()
        
    membership = OrgMembership(
        id=uuid.uuid4(),
        organization_id=oid,
        person_id=pid,
        role_id=role.id,
        start_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    async_db.add(membership)
    
    await async_db.commit()
    await async_db.refresh(user)
    return user, password


@pytest.mark.asyncio
async def test_refresh_token_rotation(async_client, test_user, async_db):
    """
    Teste 1 (Rotation):
    - Faz login e obtém refresh_token.
    - Faz o refresh.
    - Verifica se o antigo foi revogado e um novo foi criado.
    """
    user, password = test_user
    # 1. Login (OAuth2 usa data/form, não json)
    login_data = {
        "username": user.email,
        "password": password
    }
    response = await async_client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    old_refresh_token = data["refresh_token"]
    old_rt_hash = hash_token(old_refresh_token)

    # Verificar no DB que o token existe e não está revogado
    stmt = select(RefreshToken).where(RefreshToken.token_hash == old_rt_hash)
    result = await async_db.execute(stmt)
    db_old_token = result.scalar_one_or_none()
    assert db_old_token is not None
    assert db_old_token.revoked_at is None
    old_token_id = db_old_token.id

    # 2. Refresh
    refresh_payload = {"refresh_token": old_refresh_token}
    response = await async_client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == 200
    refresh_data = response.json()
    new_refresh_token = refresh_data["refresh_token"]
    assert new_refresh_token != old_refresh_token

    # 3. Validar no DB
    await async_db.refresh(db_old_token)
    assert db_old_token.revoked_at is not None

    # Verificar novo token
    new_rt_hash = hash_token(new_refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == new_rt_hash)
    result = await async_db.execute(stmt)
    db_new_token = result.scalar_one_or_none()
    assert db_new_token is not None
    assert db_new_token.parent_id == old_token_id
    assert db_new_token.revoked_at is None


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(async_client, test_user, async_db):
    """
    Teste 2 (Reuse Detection):
    - Faz o fluxo de rotação (Login -> Refresh).
    - Tenta usar o token antigo de novo.
    - Deve retornar 401 e revogar TODAS as sessões do usuário ( Kill Switch).
    """
    user, password = test_user
    # 1. Setup: Login + Refresh para ter um token revogado e um novo ativo
    login_data = {
        "username": user.email,
        "password": password
    }
    res = await async_client.post("/api/v1/auth/login", data=login_data)
    assert res.status_code == 200
    user_id = res.json()["user_id"]
    old_token = res.json()["refresh_token"]
    
    # Primeiro refresh (OK)
    res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})
    assert res.status_code == 200
    new_token = res.json()["refresh_token"]
    new_rt_hash = hash_token(new_token)

    # Verificar que o novo token está ativo no DB
    stmt = select(RefreshToken).where(RefreshToken.token_hash == new_rt_hash)
    result = await async_db.execute(stmt)
    db_new_token = result.scalar_one()
    assert db_new_token.revoked_at is None

    # 2. Tentativa de reuso do token antigo
    res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": old_token})
    assert res.status_code == 401
    assert "Sessão encerrada por segurança" in res.text

    # 3. Kill Switch: Verificar que o novo token também foi revogado
    await async_db.refresh(db_new_token)
    assert db_new_token.revoked_at is not None

    # Verificar que todas as sessões do usuário estão revogadas
    stmt = select(RefreshToken).where(RefreshToken.user_id == UUID(user_id), RefreshToken.revoked_at.is_(None))
    result = await async_db.execute(stmt)
    active_tokens = result.scalars().all()
    assert len(active_tokens) == 0


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(async_client, test_user, async_db):
    """
    Teste 3 (Logout):
    - Login.
    - Logout passando o refresh_token.
    - Garantir revogação no DB.
    """
    user, password = test_user
    # 1. Login
    login_data = {
        "username": user.email,
        "password": password
    }
    res = await async_client.post("/api/v1/auth/login", data=login_data)
    assert res.status_code == 200
    token = res.json()["refresh_token"]
    token_hash = hash_token(token)

    # 2. Logout (passando o token no body conforme implementado no auth.py)
    access_token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    res = await async_client.post("/api/v1/auth/logout", json={"refresh_token": token}, headers=headers)
    assert res.status_code == 204

    # 3. Verificar no DB
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await async_db.execute(stmt)
    db_token = result.scalar_one()
    assert db_token.revoked_at is not None
