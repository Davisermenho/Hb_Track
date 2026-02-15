"""
Fixtures de teste com isolamento transacional via savepoint.
Ref: FASE 2 — Núcleo do backend (tests/conftest.py template)

Cada teste roda dentro de um savepoint que é revertido ao final,
garantindo isolamento total sem alteração permanente no banco.

Suporta testes síncronos (Session) e assíncronos (AsyncSession).
"""
import os
import sys
from pathlib import Path
import asyncio

# Add repo-root scripts to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# IMPORTANTE: Setar ENV=test ANTES de qualquer importação da app
# Isso garante que rate_limit.py use limite alto (10000/min)
os.environ["ENV"] = "test"

# Windows + psycopg: exige SelectorEventLoop (Proactor não é suportado)
if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.db import engine
from app.core.config import settings
from app.main import app

# AsyncEngine para testes assíncronos
# Converte sslmode=require para ssl=True (asyncpg usa formato diferente)
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
# Remove parâmetros incompatíveis com asyncpg
if "sslmode=" in async_db_url:
    async_db_url = async_db_url.split("?")[0]  # Remove query params
    async_db_url += "?ssl=require"

def _create_async_test_engine():
    return create_async_engine(
        async_db_url,
        pool_pre_ping=True,
        future=True,
        poolclass=NullPool,
    )


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Fixture com isolamento transacional real via savepoint.
    - Conexão e transação raiz aberta
    - Session ligada à conexão da transação raiz
    - Savepoint para cada teste
    - Rollback automático ao final
    """
    # Conexão e transação raiz
    connection = engine.connect()
    transaction = connection.begin()

    # Session ligada à conexão da transação raiz
    TestingSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    session = TestingSessionLocal()

    # Savepoint para cada teste
    nested = connection.begin_nested()

    # Recria savepoint após commits dentro do teste
    @sa.event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess: Session, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest_asyncio.fixture(scope="function")
async def async_db() -> AsyncSession:
    """
    Fixture async com isolamento transacional via savepoint.
    Para uso em testes assíncronos (async def test_*).
    
    - Conexão async e transação raiz aberta
    - AsyncSession ligada à conexão da transação raiz
    - Savepoint para cada teste
    - Rollback automático ao final
    """
    # Conexão e transação raiz
    async_engine = _create_async_test_engine()
    async with async_engine.connect() as connection:
        async with connection.begin() as transaction:
            # AsyncSession ligada à conexão da transação raiz
            TestingAsyncSessionLocal = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            session = TestingAsyncSessionLocal()

            # Savepoint para cada teste
            async with connection.begin_nested():
                try:
                    yield session
                finally:
                    await session.close()
                    await transaction.rollback()
    await async_engine.dispose()


@pytest.fixture(scope="function")
def client(db: Session):
    """
    TestClient com override de get_db para usar a sessão isolada.
    """
    from app.core.db import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass  # Não fecha, a fixture db gerencia

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ============================================
# FIXTURES DE AUTENTICAÇÃO
# ============================================
import os
from dotenv import load_dotenv

# Carrega variáveis do .env.test se existir
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.test'))

# Cache de cookies para evitar rate limiting
_superadmin_cookies_cache = None
_treinador_cookies_cache = None

@pytest.fixture(scope="session")
def superadmin_credentials():
    """Retorna credenciais do superadmin do .env.test"""
    return {
        "email": os.getenv("TEST_SUPERADMIN_EMAIL", "admin@hbtracking.com"),
        "password": os.getenv("TEST_SUPERADMIN_PASSWORD", "Admin@123")
    }


@pytest.fixture(scope="session")
def treinador_credentials():
    """Retorna credenciais do treinador do .env.test"""
    return {
        "email": os.getenv("TEST_TREINADOR_EMAIL", "e2e.treinador@teste.com"),
        "password": os.getenv("TEST_TREINADOR_PASSWORD", "Admin@123"),
    }

@pytest.fixture(scope="function")
def superadmin_cookies(client, superadmin_credentials):
    """
    Retorna cookies de autenticação de superadmin.
    Usa cache de sessão para evitar rate limiting.
    """
    global _superadmin_cookies_cache
    
    # Usar cache se disponível
    if _superadmin_cookies_cache is not None:
        return _superadmin_cookies_cache
    
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": superadmin_credentials["email"],
            "password": superadmin_credentials["password"]
        }
    )
    if response.status_code == 429:
        pytest.skip("Rate limited - aguarde alguns segundos")
    if response.status_code != 200:
        pytest.skip(f"Login falhou: {response.status_code} - {response.text[:100]}")
    
    _superadmin_cookies_cache = dict(response.cookies)
    return _superadmin_cookies_cache


@pytest.fixture(scope="function")
def auth_client(client, superadmin_cookies):
    """
    TestClient já autenticado como superadmin.
    Uso: response = auth_client.get("/api/v1/teams")
    """
    class AuthenticatedClient:
        def __init__(self, test_client, cookies):
            self._client = test_client
            self._cookies = cookies
        
        def get(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.get(url, **kwargs)
        
        def post(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.post(url, **kwargs)
        
        def patch(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.patch(url, **kwargs)
        
        def delete(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.delete(url, **kwargs)
    
    return AuthenticatedClient(client, superadmin_cookies)


@pytest.fixture(scope="function")
def treinador_cookies(client, treinador_credentials):
    """
    Retorna cookies de autenticação de treinador.
    Usa cache de sessão para evitar rate limiting.
    """
    global _treinador_cookies_cache

    if _treinador_cookies_cache is not None:
        return _treinador_cookies_cache

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": treinador_credentials["email"],
            "password": treinador_credentials["password"],
        },
    )
    if response.status_code == 429:
        pytest.skip("Rate limited - aguarde alguns segundos")
    if response.status_code != 200:
        pytest.skip(f"Login treinador falhou: {response.status_code} - {response.text[:100]}")

    _treinador_cookies_cache = dict(response.cookies)
    return _treinador_cookies_cache


@pytest.fixture(scope="function")
def treinador_auth_client(client, treinador_cookies):
    """
    TestClient já autenticado como treinador.
    Uso: response = treinador_auth_client.get("/api/v1/teams")
    """
    class AuthenticatedClient:
        def __init__(self, test_client, cookies):
            self._client = test_client
            self._cookies = cookies

        def get(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.get(url, **kwargs)

        def post(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.post(url, **kwargs)

        def patch(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.patch(url, **kwargs)

        def delete(self, url, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return self._client.delete(url, **kwargs)

    return AuthenticatedClient(client, treinador_cookies)


@pytest.fixture(scope="function")
def test_team_id(auth_client, db):
    """
    Retorna o ID de uma equipe ATIVA (deleted_at IS NULL) que pertence à organização do usuário.
    Usa a rota GET /teams que já filtra por organização do usuário autenticado.
    """
    response = auth_client.get("/api/v1/teams", params={"limit": 100})
    if response.status_code != 200:
        pytest.skip("Não foi possível obter equipes")
    
    data = response.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    
    # Filtrar por equipes ATIVAS (deleted_at = None)
    active_items = [t for t in items if t.get("deleted_at") is None]
    
    if not active_items:
        pytest.skip("Nenhuma equipe ATIVA encontrada na organização do usuário")
    
    return str(active_items[0]["id"])


@pytest.fixture(scope="function")
def treinador_team_id(treinador_auth_client, db):
    """
    Retorna o ID de uma equipe ATIVA acessível ao treinador.
    Usa a rota GET /teams que filtra por team_membership.
    """
    response = treinador_auth_client.get("/api/v1/teams", params={"limit": 100})
    if response.status_code != 200:
        pytest.skip("Não foi possível obter equipes para o treinador")

    data = response.json()
    items = data.get("items", data) if isinstance(data, dict) else data

    active_items = [t for t in items if t.get("deleted_at") is None]
    if not active_items:
        pytest.skip("Nenhuma equipe ATIVA encontrada para o treinador")

    return str(active_items[0]["id"])


# ============================================
# FIXTURES PARA TESTES DE INVARIANTES (AUTH)
# ============================================

@pytest.fixture(scope="function")
def auth_headers(superadmin_cookies):
    """
    Retorna header de autenticação Bearer (apenas para testes de precedência).
    Na prática, extrai o token do cookie e formata como Bearer header.
    """
    # Extrair token JWT do cookie (assumir formato simples)
    token = superadmin_cookies.get("hb_access_token") or superadmin_cookies.get("access_token")
    if not token:
        pytest.skip("Token não encontrado nos cookies de superadmin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_cookies(superadmin_cookies):
    """
    Alias direto para superadmin_cookies (para compatibilidade com nomenclatura de testes).
    """
    return superadmin_cookies


@pytest.fixture(scope="function")
def test_season_data():
    """
    Payload mínimo para criar uma Season (usado em testes de CSRF).
    """
    return {
        "name": "Test Season 2025",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "status": "active"
    }


@pytest.fixture(scope="function")
def test_training_session_data(test_team_id):
    """
    Payload mínimo para criar uma TrainingSession (usado em testes de deprecação Bearer).
    """
    return {
        "team_id": test_team_id,
        "date": "2025-06-15",
        "duration_minutes": 90,
        "session_type": "technical",
        "notes": "Test session for Bearer deprecation invariant"
    }
