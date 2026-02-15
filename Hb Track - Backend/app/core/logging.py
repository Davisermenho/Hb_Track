"""
Logging estruturado JSON

Para produção, usar logging em JSON para integração com:
- CloudWatch (AWS)
- Stackdriver (GCP)
- Application Insights (Azure)

Referências RAG:
- R31: Ações críticas auditáveis
- R32: Log obrigatório (quem, quando, o quê)
"""
import logging
import json
from datetime import datetime, timezone
from typing import Any
from typing import Dict, Optional
from uuid import uuid4
import logging as _logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog


class JSONFormatter(logging.Formatter):
    """Formatter para logs em JSON"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Adicionar campos extras
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "person_id"):
            log_data["person_id"] = record.person_id

        if hasattr(record, "organization_id"):
            log_data["organization_id"] = record.organization_id

        if hasattr(record, "method"):
            log_data["method"] = record.method

        if hasattr(record, "path"):
            log_data["path"] = record.path

        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip

        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(env: str, log_level: str) -> None:
    """
    Configura logging conforme ambiente

    Args:
        env: "local", "staging", "production"
        log_level: "DEBUG", "INFO", "WARNING", "ERROR"
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()

    if env == "production":
        # JSON em produção
        console_handler.setFormatter(JSONFormatter())
    else:
        # Human-readable em dev
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    # Reduzir verbosidade de bibliotecas terceiras
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_request_id(request: Request) -> str:
    """Retorna `X-Request-ID` se presente ou gera um UUID v4."""
    rid = request.headers.get("X-Request-ID")
    if rid:
        return rid
    return str(uuid4())


def get_client_ip(request: Request) -> str:
    """Extrai o IP do cliente do objeto Request, vazio se não disponível."""
    try:
        return request.client.host
    except Exception:
        return ""


def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "")[:200]


async def emit_auth_audit(db: AsyncSession, action: str, entity: str = "auth", entity_id: Optional[str] = None, actor_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Insere um registro em `audit_logs` (append-only).

    Usa `AsyncSession` passado pelo handler. Em caso de falha, faz rollback
    e loga a exceção, mas não propaga (não deve quebrar o fluxo de autenticação).
    """
    try:
        audit = AuditLog(
            entity=entity,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            context=context or {},
            old_value=None,
            new_value=None,
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        _logging.getLogger(__name__).exception("Failed to emit audit log: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
