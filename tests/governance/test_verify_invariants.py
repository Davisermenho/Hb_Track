"""
Suite de testes para verify_invariants_tests.py

Testa parser, classifier, AST analyzer e validators com fixtures válidas/inválidas
"""
import tempfile
from pathlib import Path
import pytest

# Import do script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'docs' / 'scripts'))
from verify_invariants_tests import (
    InvariantsParser,
    FileClassifier,
    ASTAnalyzer,
    RuleValidator,
    InvariantSpec,
    TestFile
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_invariants_md(tmp_path):
    """Cria INVARIANTS_TRAINING.md de exemplo"""
    content = """
# INVARIANTS_TRAINING.md

## 1) Confirmadas

### INV-TRAIN-001 — Test invariant
* **Status**: CONFIRMADA
* **Classe**: A
* **Escopo**: `training_sessions`
* **Evidência**: `ck_training_sessions_focus_sum` (`schema.sql:2640`)

### INV-TRAIN-002 — Test router
* **Status**: CONFIRMADA
* **Classe**: D
* **Escopo**: attendance API
* **Evidência**: `app/api/v1/routers/attendance.py:54`

### INV-TRAIN-017 — Inactive
* **Status**: INATIVA
* **Classe**: F
"""
    md_file = tmp_path / "INVARIANTS_TRAINING.md"
    md_file.write_text(content)
    return md_file


@pytest.fixture
def valid_class_a_test(tmp_path):
    """Arquivo de teste válido Classe A"""
    content = '''"""
Test: INV-TRAIN-001

Classe: A (DB constraint)

Obrigação A:
- training_sessions.focus_physical NOT NULL
- training_sessions.focus_technical NOT NULL
- CHECK constraint validates sum

Obrigação B:
- SQLSTATE: 23514 (CHECK violation)
- constraint_name: ck_training_sessions_focus_sum
"""
import pytest
from sqlalchemy.exc import IntegrityError
from uuid import uuid4


class TestInvTrain001FocusSum:
    
    async def test_valid_case__sum_at_120(self, async_db):
        """Valid: sum exactly 120"""
        org_id = uuid4()
        team_id = uuid4()
        session_id = uuid4()
        
        await async_db.execute(
            "INSERT INTO training_sessions (id, team_id, focus_physical, focus_technical) "
            "VALUES (:id, :team_id, 60, 60)",
            {"id": session_id, "team_id": team_id}
        )
        await async_db.flush()
    
    async def test_invalid_case_1__sum_exceeds_120(self, async_db):
        """Invalid: sum 121"""
        with pytest.raises(IntegrityError) as exc:
            session_id = uuid4()
            await async_db.execute(
                "INSERT INTO training_sessions (id, team_id, focus_physical, focus_technical) "
                "VALUES (:id, :team_id, 61, 60)",
                {"id": session_id, "team_id": uuid4()}
            )
            await async_db.flush()
        
        orig = exc.value.orig
        assert orig.pgcode == "23514"
        diag = orig.diag
        assert diag.constraint_name == "ck_training_sessions_focus_sum"
        await async_db.rollback()
    
    async def test_invalid_case_2__negative_focus(self, async_db):
        """Invalid: negative value"""
        with pytest.raises(IntegrityError) as exc:
            session_id = uuid4()
            await async_db.execute(
                "INSERT INTO training_sessions (id, team_id, focus_physical, focus_technical) "
                "VALUES (:id, :team_id, -1, 60)",
                {"id": session_id, "team_id": uuid4()}
            )
            await async_db.flush()
        
        orig = exc.value.orig
        assert orig.pgcode == "23514"
        await async_db.rollback()
'''
    test_file = tmp_path / "test_inv_train_001_focus_sum.py"
    test_file.write_text(content)
    return test_file


@pytest.fixture
def invalid_class_a_test__no_rollback(tmp_path):
    """Arquivo Classe A inválido (falta rollback)"""
    content = '''"""
Test: INV-TRAIN-002

Obrigação A: training_sessions.status NOT NULL
Obrigação B: SQLSTATE 23514, constraint_name ck_status
"""
import pytest
from sqlalchemy.exc import IntegrityError
from uuid import uuid4


class TestInvTrain002:
    
    async def test_valid(self, async_db):
        pass
    
    async def test_invalid(self, async_db):
        with pytest.raises(IntegrityError) as exc:
            await async_db.execute("INSERT INTO training_sessions (id) VALUES (:id)", {"id": uuid4()})
            await async_db.flush()
        
        orig = exc.value.orig
        assert orig.pgcode == "23514"
        # MISSING: await async_db.rollback()
'''
    test_file = tmp_path / "test_inv_train_002_invalid.py"
    test_file.write_text(content)
    return test_file


@pytest.fixture
def invalid_class_d_test__uses_async_db(tmp_path):
    """Arquivo Classe D inválido (usa async_db)"""
    content = '''"""
Test: INV-TRAIN-003

Classe: D (Router)

Obrigação A: router requires auth
Obrigação B: operationId attendance_api_v1
"""
from fastapi.testclient import TestClient


class TestInvTrain003:
    
    def test_without_auth(self, client):
        response = client.get("/api/v1/attendance")
        assert response.status_code == 401
    
    def test_with_db(self, async_db, auth_client):
        # FORBIDDEN: Classe D não pode usar async_db
        pass
'''
    test_file = tmp_path / "test_inv_train_003_router.py"
    test_file.write_text(content)
    return test_file


# ============================================================================
# TESTS: PARSER
# ============================================================================

def test_parser_extracts_confirmed_invariants(sample_invariants_md):
    """Parser extrai apenas invariantes confirmadas"""
    parser = InvariantsParser()
    invariants = parser.parse(sample_invariants_md)
    
    assert len(invariants) == 2
    assert invariants[0].id == "INV-TRAIN-001"
    assert invariants[0].class_type == "A"
    assert invariants[1].id == "INV-TRAIN-002"
    assert invariants[1].class_type == "D"


def test_parser_ignores_inactive(sample_invariants_md):
    """Parser ignora invariantes inativas"""
    parser = InvariantsParser()
    invariants = parser.parse(sample_invariants_md)
    
    inv_ids = [inv.id for inv in invariants]
    assert "INV-TRAIN-017" not in inv_ids


def test_parser_extracts_evidence(sample_invariants_md):
    """Parser extrai evidências (constraints, file:line)"""
    parser = InvariantsParser()
    invariants = parser.parse(sample_invariants_md)
    
    inv001 = next(inv for inv in invariants if inv.id == "INV-TRAIN-001")
    assert "ck_training_sessions_focus_sum" in inv001.evidence


def test_parser_detects_split_mixed_error(tmp_path):
    """Parser detecta erro de ID base + split coexistindo"""
    content = """
### INV-TRAIN-001 — Base
* **Status**: CONFIRMADA
* **Classe**: A

### INV-TRAIN-001-A — Split
* **Status**: CONFIRMADA
* **Classe**: A
"""
    md_file = tmp_path / "test.md"
    md_file.write_text(content)
    
    parser = InvariantsParser()
    with pytest.raises(ValueError, match="ID_SPLIT_MIXED"):
        parser.parse(md_file)


# ============================================================================
# TESTS: FILE CLASSIFIER
# ============================================================================

def test_classifier_finds_principal_files(tmp_path):
    """Classifier identifica arquivos principais"""
    (tmp_path / "test_inv_train_001_focus.py").touch()
    (tmp_path / "test_inv_train_002_wellness.py").touch()
    
    classifier = FileClassifier(tmp_path)
    files_by_inv = classifier.find_test_files()
    
    assert "INV-TRAIN-001" in files_by_inv
    assert len(files_by_inv["INV-TRAIN-001"]) == 1
    assert files_by_inv["INV-TRAIN-001"][0].is_principal


def test_classifier_identifies_runtime_supplementary(tmp_path):
    """Classifier identifica arquivos *_runtime.py como suplementares"""
    (tmp_path / "test_inv_train_001_focus.py").touch()
    (tmp_path / "test_inv_train_001_focus_runtime.py").touch()
    
    classifier = FileClassifier(tmp_path)
    files_by_inv = classifier.find_test_files()
    
    files = files_by_inv["INV-TRAIN-001"]
    assert len(files) == 2
    
    principal = [f for f in files if f.is_principal]
    runtime = [f for f in files if f.is_runtime]
    
    assert len(principal) == 1
    assert len(runtime) == 1


# ============================================================================
# TESTS: AST ANALYZER
# ============================================================================

def test_ast_analyzer_detects_class_name(valid_class_a_test):
    """AST analyzer detecta nome da classe"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    assert analysis.class_name == "TestInvTrain001FocusSum"


def test_ast_analyzer_counts_valid_invalid_tests(valid_class_a_test):
    """AST analyzer conta testes válidos e inválidos"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    assert analysis.valid_test_count == 1
    assert analysis.invalid_test_count == 2


def test_ast_analyzer_detects_fixtures_used(valid_class_a_test):
    """AST analyzer detecta fixtures usados"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    assert "async_db" in analysis.fixtures_used


def test_ast_analyzer_detects_patterns(valid_class_a_test):
    """AST analyzer detecta padrões conformes"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    assert analysis.patterns_found['pytest_raises_integrity']
    assert analysis.patterns_found['pgcode_structured']
    assert analysis.patterns_found['constraint_structured']
    assert analysis.patterns_found['rollback_called']
    assert analysis.patterns_found['uuid4_used']


def test_ast_analyzer_detects_missing_rollback(invalid_class_a_test__no_rollback):
    """AST analyzer detecta ausência de rollback"""
    analyzer = ASTAnalyzer(invalid_class_a_test__no_rollback)
    analysis = analyzer.analyze()
    
    assert not analysis.patterns_found['rollback_called']


def test_ast_analyzer_extracts_docstrings(valid_class_a_test):
    """AST analyzer extrai docstrings"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    assert 'module' in analysis.docstrings
    assert 'Obrigação A' in analysis.docstrings['module']
    assert 'Obrigação B' in analysis.docstrings['module']


# ============================================================================
# TESTS: RULE VALIDATOR
# ============================================================================

def test_validator_coverage_missing():
    """Validator detecta cobertura faltante"""
    invariants = [
        InvariantSpec("INV-TRAIN-001", "CONFIRMADA", "A", "sessions", [])
    ]
    files_by_inv = {}
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_coverage(invariants, files_by_inv)
    
    assert len(violations) == 1
    assert violations[0].code == "COVERAGE_MISSING"
    assert violations[0].inv_id == "INV-TRAIN-001"


def test_validator_coverage_duplicate(tmp_path):
    """Validator detecta arquivos duplicados"""
    file1 = TestFile(tmp_path / "test_inv_train_001_a.py", "INV-TRAIN-001", False)
    file2 = TestFile(tmp_path / "test_inv_train_001_b.py", "INV-TRAIN-001", False)
    
    invariants = [
        InvariantSpec("INV-TRAIN-001", "CONFIRMADA", "A", "sessions", [])
    ]
    files_by_inv = {"INV-TRAIN-001": [file1, file2]}
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_coverage(invariants, files_by_inv)
    
    assert len(violations) == 1
    assert violations[0].code == "COVERAGE_DUPLICATE"


def test_validator_class_a_min_tests(valid_class_a_test):
    """Validator Classe A: valida mínimo de testes"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    # Modificar análise para simular insuficiência
    analysis.valid_test_count = 0
    analysis.invalid_test_count = 1
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_class_a(analysis, valid_class_a_test)
    
    codes = [v.code for v in violations]
    assert "A_MIN_VALID" in codes
    assert "A_MIN_INVALID" in codes


def test_validator_class_a_requires_async_db(valid_class_a_test):
    """Validator Classe A: exige async_db"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    analysis.fixtures_used = set()  # Remover fixtures
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_class_a(analysis, valid_class_a_test)
    
    codes = [v.code for v in violations]
    assert "A_REQUIRES_ASYNC_DB" in codes


def test_validator_class_a_requires_rollback(invalid_class_a_test__no_rollback):
    """Validator Classe A: exige rollback"""
    analyzer = ASTAnalyzer(invalid_class_a_test__no_rollback)
    analysis = analyzer.analyze()
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_class_a(analysis, invalid_class_a_test__no_rollback)
    
    codes = [v.code for v in violations]
    assert "A_REQUIRES_ROLLBACK" in codes


def test_validator_class_d_forbids_async_db(invalid_class_d_test__uses_async_db):
    """Validator Classe D: proíbe async_db"""
    analyzer = ASTAnalyzer(invalid_class_d_test__uses_async_db)
    analysis = analyzer.analyze()
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_class_d(analysis, invalid_class_d_test__uses_async_db)
    
    codes = [v.code for v in violations]
    assert "D_FORBIDS_ASYNC_DB" in codes


def test_validator_obligations_strict_mode(valid_class_a_test):
    """Validator exige Obrigação A/B em modo strict"""
    analyzer = ASTAnalyzer(valid_class_a_test)
    analysis = analyzer.analyze()
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_obligations(analysis, valid_class_a_test)
    
    # Arquivo válido não deve ter violações
    assert len(violations) == 0


def test_validator_obligations_missing(tmp_path):
    """Validator detecta Obrigação A/B ausente"""
    content = '''"""
Test without obligations
"""
class TestInvTrain001:
    pass
'''
    test_file = tmp_path / "test_inv_train_001.py"
    test_file.write_text(content)
    
    analyzer = ASTAnalyzer(test_file)
    analysis = analyzer.analyze()
    
    validator = RuleValidator(level='strict')
    violations = validator.validate_obligations(analysis, test_file)
    
    codes = [v.code for v in violations]
    assert "OBLIG_A_MISSING" in codes
    assert "OBLIG_B_MISSING" in codes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
