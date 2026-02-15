"""
Testes do módulo core/auth.
Ref: FASE 2 — Núcleo do backend
FASE 6 — Atualizado para JWT real
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.auth import (
    MockUser,
    require_role,
    ExecutionContext,
    get_mock_context,
)


class TestMockUser:
    """Testes da classe MockUser (compatibilidade FASE 2)."""

    def test_mock_user_default_values(self):
        """Verifica valores padrão do MockUser."""
        user = MockUser()
        
        # Valores padrão definidos em app.core.auth.MockUser.__init__
        assert user.user_id == "09cd9e07-3a95-4d1e-8f19-d3d81e1dd8b4"  # superadmin@seed.local
        assert user.organization_id == "85b5a651-6677-4a6a-a08f-60e657a624a2"  # Clube Novo
        assert user.role == "coordenador"
        assert user.permissions == {"*": True}

    def test_mock_user_custom_values(self):
        """Verifica MockUser com valores customizados."""
        user = MockUser(
            user_id="custom-id",
            role="treinador",
            permissions=["athlete:read", "athlete:create"],
        )
        
        assert user.user_id == "custom-id"
        assert user.role == "treinador"
        assert user.permissions == {"athlete:read": True, "athlete:create": True}

    def test_has_permission_wildcard(self):
        """MockUser com '*' tem todas as permissões."""
        user = MockUser(permissions=["*"])
        
        assert user.has_permission("anything") is True
        assert user.has_permission("athlete:create") is True

    def test_has_permission_specific(self):
        """MockUser com permissões específicas."""
        user = MockUser(permissions=["athlete:read", "athlete:create"])
        
        assert user.has_permission("athlete:read") is True
        assert user.has_permission("athlete:create") is True
        assert user.has_permission("athlete:delete") is False

    def test_to_dict(self):
        """Verifica serialização para dict."""
        user = MockUser()
        data = user.to_dict()
        
        assert "user_id" in data
        assert "role" in data
        assert "organization_id" in data
        assert data["role"] == "coordenador"


class TestExecutionContext:
    """Testes da classe ExecutionContext (FASE 6)."""
    
    def test_execution_context_creation(self):
        """Verifica criação de ExecutionContext."""
        ctx = ExecutionContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="test@example.com",
            person_id=UUID("00000000-0000-0000-0000-000000000002"),
            membership_id=UUID("00000000-0000-0000-0000-000000000003"),
            organization_id=UUID("00000000-0000-0000-0000-000000000004"),
            role_code="treinador",
            is_superadmin=False,
            request_id="test-request-id",
            timestamp=datetime.now(timezone.utc),
        )
        
        assert ctx.user_id == UUID("00000000-0000-0000-0000-000000000001")
        assert ctx.organization_id == UUID("00000000-0000-0000-0000-000000000004")
        assert ctx.role_code == "treinador"
        assert ctx.is_superadmin is False
    
    def test_can_bypass_rules(self):
        """Verifica que apenas superadmin pode ignorar regras (R3)."""
        ctx_normal = ExecutionContext(
            user_id=uuid4(),
            email="normal@test.com",
            person_id=uuid4(),
            membership_id=uuid4(),
            organization_id=uuid4(),
            role_code="coordenador",
            is_superadmin=False,
            request_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        
        ctx_super = ExecutionContext(
            user_id=uuid4(),
            email="super@test.com",
            person_id=uuid4(),
            membership_id=None,
            organization_id=uuid4(),
            role_code="superadmin",
            is_superadmin=True,
            request_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        
        assert ctx_normal.can_bypass_rules() is False
        assert ctx_super.can_bypass_rules() is True
    
    def test_has_active_membership(self):
        """Verifica vínculo ativo (R42)."""
        ctx_with_membership = ExecutionContext(
            user_id=uuid4(),
            email="member@test.com",
            person_id=uuid4(),
            membership_id=uuid4(),
            organization_id=uuid4(),
            role_code="treinador",
            is_superadmin=False,
            request_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        
        ctx_superadmin = ExecutionContext(
            user_id=uuid4(),
            email="super@test.com",
            person_id=uuid4(),
            membership_id=None,
            organization_id=uuid4(),
            role_code="superadmin",
            is_superadmin=True,
            request_id="test",
            timestamp=datetime.now(timezone.utc),
        )
        
        assert ctx_with_membership.has_active_membership() is True
        assert ctx_superadmin.has_active_membership() is True  # Superadmin sempre pode
    
    def test_to_audit_dict(self):
        """Verifica conversão para dict de auditoria (R31, R32)."""
        ctx = ExecutionContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="audit@test.com",
            person_id=UUID("00000000-0000-0000-0000-000000000002"),
            membership_id=UUID("00000000-0000-0000-0000-000000000003"),
            organization_id=UUID("00000000-0000-0000-0000-000000000004"),
            role_code="coordenador",
            is_superadmin=False,
            request_id="req-123",
            timestamp=datetime.now(timezone.utc),
        )
        
        audit = ctx.to_audit_dict()
        
        assert audit["actor_user_id"] == "00000000-0000-0000-0000-000000000001"
        assert audit["actor_role"] == "coordenador"
        assert audit["request_id"] == "req-123"
        assert audit["is_superadmin"] is False


class TestMockContext:
    """Testes da função get_mock_context."""
    
    def test_get_mock_context_returns_execution_context(self):
        """get_mock_context retorna ExecutionContext."""
        ctx = get_mock_context()
        
        assert isinstance(ctx, ExecutionContext)
        # O mock context usa dados do banco, não valores fixos
        assert ctx.role_code in ["coordenador", "dirigente", "superadmin", "treinador", "atleta"]


class TestRequireRole:
    """Testes da função require_role."""

    def test_require_role_returns_callable(self):
        """require_role retorna uma função callable."""
        check = require_role("dirigente")
        
        assert callable(check)
