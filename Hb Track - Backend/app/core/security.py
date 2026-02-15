"""
Segurança: JWT, password hashing

FASE 6 - Endurecimento e Segurança

Referências RAG:
- R3: Super Admin (pode operar sem vínculo)
- R42: Vínculo ativo obrigatório (exceto superadmin)
- R25/R26: Permissões por papel
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from types import SimpleNamespace
import hashlib
import hmac
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings
from uuid import UUID, uuid4

# Compat: passlib 1.7 expects bcrypt.__about__.__version__, which bcrypt 4.3 removed
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = SimpleNamespace(__version__=getattr(bcrypt, "__version__", "<unknown>"))

from passlib.context import CryptContext

# Password hashing usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash de senha usando bcrypt
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash bcrypt da senha
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica senha contra hash
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash bcrypt armazenado
        
    Returns:
        True se senha correta, False caso contrário
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria JWT access token

    Payload esperado:
    - sub: user_id (UUID como string)
    - person_id: UUID como string
    - membership_id: UUID como string ou None
    - role_code: str (dirigente, coordenador, treinador, atleta)
    - is_superadmin: bool
    - organization_id: UUID como string
    - exp: timestamp de expiração (adicionado automaticamente)

    Args:
        data: Dict com claims do JWT
        expires_delta: Duração do token (padrão: settings.JWT_EXPIRES_MINUTES)

    Returns:
        Token JWT assinado

    Referências RAG:
    - R3: Superadmin pode não ter membership_id
    - R42: Vínculo ativo obrigatório para não-superadmin
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    # PyJWT < 2.0 retorna bytes, >= 2.0 retorna str
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode("utf-8")

    return encoded_jwt


def hash_token(token: str) -> str:
    """
    Gera hash SHA-256 de um token para armazenamento seguro.
    
    Usado para Refresh Tokens (Fase 2).
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verifica se um token corresponde ao hash armazenado.
    """
    current_hash = hashlib.sha256(token.encode()).hexdigest()
    return hmac.compare_digest(current_hash, token_hash)


def decode_access_token(token: str) -> dict:
    """
    Decodifica JWT

    Args:
        token: JWT string

    Returns:
        Payload decodificado

    Raises:
        JWTError: Se token inválido ou expirado
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria refresh token (mais longo que access token)
    
    Args:
        user_id: ID do usuário
        expires_delta: Duração do token (padrão: 7 dias)
        
    Returns:
        Refresh token JWT
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": str(uuid4())
    }
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def decode_refresh_token(token: str) -> Optional[str]:
    """
    Decodifica refresh token
    
    Args:
        token: Refresh token JWT
        
    Returns:
        user_id se válido, None se inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None
