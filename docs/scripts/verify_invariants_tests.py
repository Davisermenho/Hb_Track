#!/usr/bin/env python3
"""
Script de Validação Binária de Testes de Invariantes

Valida conformidade dos testes de invariantes com INVARIANTS_TESTING_CANON.md.
Retorna exit code binário: 0 (pass), 2 (fail).

CONTRATO DE IDs SUPORTADOS:
- Formato base: INV-TRAIN-XXX (ex: INV-TRAIN-001)
- Formato split: INV-TRAIN-XXX-<classe><subclasse opcional> (ex: INV-TRAIN-001-A, INV-TRAIN-001-C2)
- Regra de precedência: se existir qualquer split para XXX, o ID base não pode coexistir
- Cobertura 1:1: cada INV exige exatamente 1 arquivo principal test_inv_train_XXX_*.py

USAGE:
    python verify_invariants_tests.py [--level {basic,standard,strict}] [--verbose]
    python verify_invariants_tests.py --files-changed file1.py file2.py
    python verify_invariants_tests.py --report-json report.json --report-txt report.txt

EXIT CODES:
    0: Todas validações passaram
    1: Erro de execução (parsing, filesystem)
    2: Violações ERROR encontradas (bloqueia CI/commit)

OUTPUT FORMAT (compatível com VS Code problemMatcher):
    path:line:col: LEVEL [CODE]: message — action
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# CLASS TAXONOMY (Allowed Classes)
# ============================================================================

# All classes allowed in the invariant taxonomy
ALLOWED_CLASSES = {'A', 'B', 'C1', 'C2', 'D', 'E1', 'F'}

# Classes with validators currently implemented
IMPLEMENTED_CLASSES = {'A', 'B', 'C1', 'C2', 'D', 'E1', 'F'}

# ============================================================================
# DOD-6a: LOOKUP/SEED TABLES (proibido criar linhas em testes de invariantes)
# ============================================================================

# Tabelas de catálogo/config com IDs semânticos e/ou seed estável
# Adicione novas tabelas conforme necessário
LOOKUP_TABLES = {
    'categories',
    'category',  # singular também
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_obrigacao_b(docstring_text: str) -> str:
    """
    Extrai o texto da seção 'Obrigação B' do docstring.
    
    Retorna o conteúdo entre o cabeçalho "Obrigação B" e o próximo
    "Obrigação" (A/C/D...) ou fim do texto.
    
    Args:
        docstring_text: Texto do docstring (pode ser concatenação de múltiplos)
    
    Returns:
        Texto da seção Obrigação B, ou string vazia se não encontrado
    """
    # Regex para encontrar "Obrigação B:" seguido de qualquer coisa até:
    # - próxima "Obrigação X:" (onde X é qualquer letra)
    # - fim da string
    pattern = r'Obrigação B:(.*?)(?:Obrigação [A-Z]:|$)'
    match = re.search(pattern, docstring_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    return ""


def pick_primary_docstring(docstrings_dict: Dict[str, str], inv_id: str, test_node: Optional[str]) -> str:
    """
    Seleciona o docstring primário para uma invariante específica.
    
    Regras de precedência:
    1. Docstring que contém o inv_id (ex: "INV-TRAIN-033")
    2. Docstring que contém o test_node do SPEC (ex: "TestInvTrain033WellnessPreSleepHours")
    3. Docstring da classe (chave 'class')
    4. Primeiro docstring disponível
    
    Args:
        docstrings_dict: Dict com docstrings do arquivo ('module', 'class', etc)
        inv_id: ID da invariante (ex: INV-TRAIN-033)
        test_node: Nome da classe de teste do SPEC (opcional)
    
    Returns:
        Docstring primário ou string vazia
    """
    if not docstrings_dict:
        return ""
    
    # Regra 1: procurar inv_id em qualquer docstring
    for key, docstring in docstrings_dict.items():
        if inv_id in docstring:
            return docstring
    
    # Regra 2: procurar test_node (nome da classe de teste)
    if test_node:
        for key, docstring in docstrings_dict.items():
            if test_node in docstring:
                return docstring
    
    # Regra 3: docstring da classe
    if 'class' in docstrings_dict:
        return docstrings_dict['class']
    
    # Regra 4: primeiro disponível
    return next(iter(docstrings_dict.values()))


# ============================================================================
# DATA STRUCTURES
# ============================================================================

def normalize_anchors(raw: dict, inv_id: str = None) -> dict:
    """
    Normaliza anchors para formato nested, suportando tanto flat keys quanto nested.
    
    Formato flat (entrada): {"db.table": "x", "db.constraint": "y"}
    Formato nested (entrada): {"db": {"table": "x", "constraint": "y"}}
    Formato nested (saída): {"db": {"table": "x", "constraint": "y"}}
    
    Suporta namespaces: db.*, code.*, api.*, etc.
    """
    if not raw:
        return {}
    
    normalized = {}
    
    for key, value in raw.items():
        if '.' in key:
            # Flat key: dividir em namespace.subkey
            parts = key.split('.', 1)
            namespace = parts[0]
            subkey = parts[1] if len(parts) > 1 else key
            
            if namespace not in normalized:
                normalized[namespace] = {}
            normalized[namespace][subkey] = value
        else:
            # Nested key: copiar diretamente
            if isinstance(value, dict):
                # Mesclar com existente se houver
                if key not in normalized:
                    normalized[key] = {}
                normalized[key].update(value)
            else:
                normalized[key] = value
    
    return normalized


def load_openapi_operation_ids(openapi_path: Path) -> Set[str]:
    """
    Carrega todos os operationIds do openapi.json.
    
    Args:
        openapi_path: Path para o arquivo openapi.json
        
    Returns:
        Set de operationIds encontrados
    """
    operation_ids = set()
    
    if not openapi_path.exists():
        return operation_ids
    
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            openapi_spec = json.load(f)
        
        paths = openapi_spec.get('paths', {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete'] and isinstance(details, dict):
                    op_id = details.get('operationId')
                    if op_id:
                        operation_ids.add(op_id)
    except (json.JSONDecodeError, IOError) as e:
        # Se falhar ao carregar, retorna set vazio
        pass
    
    return operation_ids


def load_openapi_index(openapi_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Carrega índice completo do OpenAPI para validação de Classe F.
    
    Args:
        openapi_path: Path para o arquivo openapi.json
        
    Returns:
        Dict mapeando operationId -> {path, method, responses, security_schemes}
    """
    index = {}
    
    if not openapi_path.exists():
        return index
    
    try:
        with open(openapi_path, 'r', encoding='utf-8') as f:
            openapi_spec = json.load(f)
        
        paths = openapi_spec.get('paths', {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete'] and isinstance(details, dict):
                    op_id = details.get('operationId')
                    if op_id:
                        responses = set(details.get('responses', {}).keys())
                        
                        # Extrair security schemes (lista de dicts [{scheme: []}])
                        security = details.get('security', [])
                        security_schemes = set()
                        if security:
                            for sec_obj in security:
                                if isinstance(sec_obj, dict):
                                    security_schemes.update(sec_obj.keys())
                        
                        index[op_id] = {
                            'path': path,
                            'method': method.upper(),
                            'responses': responses,
                            'security_schemes': security_schemes
                        }
    except (json.JSONDecodeError, IOError) as e:
        # Se falhar ao carregar, retorna dict vazio
        pass
    
    return index


@dataclass
class ProofUnit:
    """Unidade de prova normativa de uma invariante"""
    unit_key: str
    class_type: str  # A, B, C1, C2, D, E1, E2, F
    required: bool
    description: str
    anchors: Dict[str, any]


@dataclass
class InvariantSpec:
    """Especificação de uma invariante extraída de INVARIANTS_TRAINING.md"""
    id: str  # INV-TRAIN-XXX ou INV-TRAIN-XXX-A
    status: str  # CONFIRMADA, INATIVA
    test_required: bool
    units: List[ProofUnit]  # Proof units (podem ser múltiplas)
    tests: Dict[str, any]  # primary, node, coverage, runtime_optional
    canonical_id: Optional[str] = None  # Se for alias de outro INV
    legacy_reason: Optional[str] = None
    has_spec: bool = False  # Se tem bloco SPEC parseado
    
    # Legacy fields (quando SPEC não disponível)
    class_type: Optional[str] = None  # Classe única (fallback)
    scope: Optional[str] = None
    evidence: Optional[List[str]] = None
    
    @property
    def base_id(self) -> str:
        """Retorna ID base sem sufixo (INV-TRAIN-001-A -> INV-TRAIN-001)"""
        match = re.match(r'(INV-TRAIN-\d{3})', self.id)
        return match.group(1) if match else self.id
    
    @property
    def is_split(self) -> bool:
        """Verifica se é um split normativo (tem sufixo -A, -C2, etc)"""
        return bool(re.match(r'INV-TRAIN-\d{3}-[A-Z]\d*$', self.id))
    
    @property
    def is_alias(self) -> bool:
        """Verifica se é um alias de outro INV"""
        return self.canonical_id is not None
    
    @property
    def primary_classes(self) -> List[str]:
        """Retorna lista de classes requeridas"""
        if self.has_spec:
            return [unit.class_type for unit in self.units if unit.required]
        elif self.class_type:
            return [self.class_type]
        return []


@dataclass
class TestFile:
    """Arquivo de teste identificado"""
    path: Path
    inv_id: str  # INV-TRAIN-XXX detectado do nome do arquivo
    is_runtime: bool  # True se for *_runtime.py
    
    @property
    def is_principal(self) -> bool:
        return not self.is_runtime


@dataclass
class ASTAnalysis:
    """Resultado da análise AST de um arquivo de teste"""
    inv_id: str
    class_name: Optional[str]
    fixtures_used: Set[str]
    valid_test_count: int
    invalid_test_count: int  # testes com pytest.raises
    pytest_raises_exceptions: Set[str]  # exception types used in pytest.raises
    patterns_found: Dict[str, bool]  # pgcode_structured, constraint_structured, rollback, etc
    docstrings: Dict[str, str]  # 'module', 'class'
    anti_patterns: List[str]  # string_match_error, hardcoded_id, engine_creation


@dataclass
class Violation:
    """Violação de regra detectada"""
    inv_id: str
    file: str
    line: int
    col: int
    level: str  # ERROR, WARN
    code: str  # A_MIN_INVALID, COVERAGE_MISSING, etc
    message: str
    action: str  # ação sugerida em 1 linha


@dataclass
class ValidationReport:
    """Relatório final de validação"""
    pass_status: bool
    level: str
    timestamp: str
    summary: Dict[str, int]
    violations: List[Violation]


# ============================================================================
# PARSER: INVARIANTS_TRAINING.md
# ============================================================================

class InvariantsParser:
    """Parser de INVARIANTS_TRAINING.md com suporte a blocos SPEC e fallback legacy"""
    
    # Regex para detectar IDs: INV-TRAIN-XXX ou INV-TRAIN-XXX-A
    ID_PATTERN = re.compile(r'INV-TRAIN-\d{3}(?:-[A-Z]\d*)?')
    
    def parse(self, md_path: Path, strict_spec: bool = False) -> Tuple[List[InvariantSpec], List[Violation]]:
        """Parseia arquivo markdown e extrai especificações de invariantes
        
        Args:
            md_path: Path to INVARIANTS_TRAINING.md
            strict_spec: If True, SPEC invalid/missing becomes ERROR violation (no legacy fallback)
        
        Returns:
            (invariants, spec_violations): List of invariants and parsing violations
        """
        if not md_path.exists():
            raise FileNotFoundError(f"INVARIANTS_TRAINING.md not found: {md_path}")
        
        content = md_path.read_text(encoding='utf-8')
        invariants = []
        spec_violations = []
        base_ids_with_splits = set()
        
        # Store state for _parse_spec_block
        self.strict_spec = strict_spec
        self.spec_violations = spec_violations
        self.md_path = md_path
        
        # Primeiro passe: detectar splits para identificar IDs base que não devem coexistir
        for match in self.ID_PATTERN.finditer(content):
            inv_id = match.group(0)
            if '-' in inv_id.split('-', 2)[-1]:  # tem sufixo
                base = re.match(r'(INV-TRAIN-\d{3})', inv_id).group(1)
                base_ids_with_splits.add(base)
        
        # Segundo passe: extrair todas as invariantes
        sections = re.split(r'^### (INV-TRAIN-\d{3}(?:-[A-Z]\d*)?)', content, flags=re.MULTILINE)
        
        for i in range(1, len(sections), 2):
            if i + 1 >= len(sections):
                break
            
            inv_id = sections[i]
            section_content = sections[i + 1]
            
            # Verificar regra de precedência: base não pode coexistir com splits
            base_id = re.match(r'(INV-TRAIN-\d{3})', inv_id).group(1)
            is_base = (inv_id == base_id)
            
            if is_base and base_id in base_ids_with_splits:
                raise ValueError(
                    f"ID_SPLIT_MIXED: base and split coexist for {base_id}. "
                    f"Remove base section or remove split sections."
                )
            
            # Tentar parsear bloco SPEC primeiro
            spec_inv = self._parse_spec_block(inv_id, section_content)
            
            if spec_inv:
                invariants.append(spec_inv)
            else:
                # Fallback: parser legacy
                legacy_inv = self._parse_legacy(inv_id, section_content)
                invariants.append(legacy_inv)
        
        return invariants, spec_violations
    
    def _parse_spec_block(self, inv_id: str, section_content: str) -> Optional[InvariantSpec]:
        """
        Parseia bloco SPEC estruturado (YAML-like)
        
        Formato esperado:
        **SPEC**:
        ```yaml
        spec_version: "1.0"
        id: "INV-TRAIN-XXX"
        status: "CONFIRMADA"
        test_required: true
        units: [...]
        tests: {...}
        ```
        """
        # Detectar bloco SPEC
        spec_match = re.search(
            r'\*\*SPEC\*\*:\s*```(?:yaml)?\s*\n(.*?)\n```',
            section_content,
            re.DOTALL
        )
        
        if not spec_match:
            return None
        
        yaml_content = spec_match.group(1)
        
        try:
            # Parse YAML manualmente (evitar dependência PyYAML)
            spec_data = self._parse_yaml_simple(yaml_content)
            
            # Validar campos obrigatórios
            required_fields = ['spec_version', 'id', 'status', 'units', 'tests']
            for field in required_fields:
                if field not in spec_data:
                    if self.strict_spec:
                        self.spec_violations.append(Violation(
                            inv_id=inv_id,
                            file=str(self.md_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='SPEC_INVALID',
                            message=f'missing required field "{field}"',
                            action=f'add {field} to SPEC block'
                        ))
                        return None  # Skip this INV but continue parsing
                    else:
                        print(f"WARNING: SPEC_INVALID for {inv_id}: missing field '{field}'")
                        return None  # Fallback to legacy
            
            # Extrair status e test_required
            status = spec_data.get('status', 'CONFIRMADA')
            test_required = spec_data.get('test_required', True)
            
            # Ignorar invariantes inativas
            if status == 'INATIVA':
                return None
            
            # Parsear units
            units = []
            units_data = spec_data.get('units', [])
            if isinstance(units_data, list):
                for unit_data in units_data:
                    if isinstance(unit_data, dict):
                        raw_anchors = unit_data.get('anchors', {})
                        units.append(ProofUnit(
                            unit_key=unit_data.get('unit_key', ''),
                            class_type=unit_data.get('class', 'UNKNOWN'),
                            required=unit_data.get('required', True),
                            description=unit_data.get('description', ''),
                            anchors=normalize_anchors(raw_anchors, inv_id)
                        ))
            
            # Parsear tests
            tests_data = spec_data.get('tests', {})
            
            return InvariantSpec(
                id=inv_id,
                status=status,
                test_required=test_required,
                units=units,
                tests=tests_data,
                canonical_id=spec_data.get('canonical_id'),
                legacy_reason=spec_data.get('legacy_reason'),
                has_spec=True
            )
        
        except Exception as e:
            if self.strict_spec:
                self.spec_violations.append(Violation(
                    inv_id=inv_id,
                    file=str(self.md_path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='SPEC_INVALID',
                    message=f'YAML parsing failed: {str(e)}',
                    action='fix SPEC block YAML syntax'
                ))
                return None  # Skip this INV but continue parsing
            else:
                print(f"WARNING: Failed to parse SPEC block for {inv_id}: {e}")
                return None  # Fallback to legacy
    
    def _parse_yaml_simple(self, yaml_text: str) -> Dict:
        """
        Parser YAML simplificado para blocos SPEC
        Suporta apenas subset usado nos blocos SPEC
        Com suporte a "pending key" para listas/dicts aninhados e stack de listas
        """
        data = {}
        current_key = None
        current_list = None
        current_list_indent = None  # Track the indent level of the parent key of current_list
        current_dict = None
        current_nested_dict = None  # Para anchors dentro de dict
        
        # Stack de listas para restaurar contexto ao sair de listas aninhadas
        list_stack = []
        
        # Tracking pending key/list initialization with proper scoping
        pending_key = None
        pending_indent = None
        pending_target_dict = None
        
        lines = yaml_text.strip().split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Detect indentation
            indent = len(line) - len(line.lstrip())
            
            # UNWIND: Pop listas da stack quando indent retorna ao nível da chave pai (ou acima)
            while current_list is not None and current_list_indent is not None and indent <= current_list_indent:
                if list_stack:
                    current_list, current_list_indent = list_stack.pop()
                else:
                    current_list = None
                    current_list_indent = None
                    break
            
            # List item - ONLY process if line starts with '-'
            if stripped.startswith('-'):
                item_content = stripped[1:].strip()
                
                # Check if we have a pending key waiting for list
                if pending_key and pending_target_dict is not None and indent > pending_indent:
                    # Initialize pending key as list (only if not already a list)
                    existing = pending_target_dict.get(pending_key, None)
                    if not isinstance(existing, list):
                        # PUSH: Empilhar lista atual antes de criar nova
                        if current_list is not None:
                            list_stack.append((current_list, current_list_indent))
                        
                        pending_target_dict[pending_key] = []
                    current_list = pending_target_dict[pending_key]
                    current_list_indent = pending_indent  # Track indent of the KEY that owns this list
                    # Clear pending after first use
                    pending_key = None
                    pending_indent = None
                    pending_target_dict = None
                
                # If current_key has None placeholder, convert to list
                if current_key and data.get(current_key) is None:
                    # PUSH: Empilhar lista atual antes de criar nova
                    if current_list is not None:
                        list_stack.append((current_list, current_list_indent))
                    
                    data[current_key] = []
                    current_list = data[current_key]
                    current_list_indent = 0  # Root level list
                
                # Append to current_list (only if line started with '-')
                if current_list is not None:
                    if ':' in item_content:
                        # Dictionary item (novo item de lista)
                        new_dict = {}
                        key, sep, value = item_content.partition(':')
                        key = key.strip()
                        value = value.strip()
                        if value:
                            new_dict[key] = self._parse_yaml_value(value)
                        current_list.append(new_dict)
                        current_dict = new_dict
                        # CRITICAL: Reset nested_dict ao criar novo item de lista
                        current_nested_dict = None
                    else:
                        # Simple item
                        current_list.append(self._parse_yaml_value(item_content))
                        # Don't clear current_dict or current_nested_dict
                continue
            
            # Key-value pair
            if ':' in stripped:
                key, sep, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()
                
                # Clear pending if we encounter a new key at same or lower indent
                if pending_key and indent <= pending_indent:
                    pending_key = None
                    pending_indent = None
                    pending_target_dict = None
                
                # Check if we have a pending key waiting for dict
                if pending_key and pending_target_dict is not None and indent > pending_indent:
                    # Initialize pending key as dict (overwrite placeholder)
                    pending_target_dict[pending_key] = {}
                    current_nested_dict = pending_target_dict[pending_key]
                    # Clear pending
                    pending_key = None
                    pending_indent = None
                    pending_target_dict = None
                    # Now process current line in the new dict
                    current_nested_dict[key] = self._parse_yaml_value(value) if value else None
                    if not value:
                        # This key itself might start a nested structure
                        pending_key = key
                        pending_indent = indent
                        pending_target_dict = current_nested_dict
                    continue
                
                # Handle root level
                if indent == 0:
                    current_key = key
                    if value:
                        # Simple value
                        data[key] = self._parse_yaml_value(value)
                        current_list = None
                        current_dict = None
                        current_nested_dict = None
                        pending_key = None
                        pending_indent = None
                        pending_target_dict = None
                    else:
                        # Empty value - mark as pending (will be list or dict)
                        data[key] = None
                        pending_key = key
                        pending_indent = indent
                        pending_target_dict = data
                        current_list = None
                        current_dict = None
                        current_nested_dict = None
                # Handle double nested (ex: db.table dentro de anchors)
                elif current_nested_dict is not None:
                    # Check if key has dot notation (namespace.subkey)
                    if '.' in key:
                        # Split namespace and subkey
                        namespace, subkey = key.split('.', 1)
                        # Get or create namespace dict
                        if namespace not in current_nested_dict:
                            current_nested_dict[namespace] = {}
                        ns_dict = current_nested_dict[namespace]
                        
                        if value:
                            # Key with value: api.method: "GET"
                            ns_dict[subkey] = self._parse_yaml_value(value)
                        else:
                            # Key without value: api.responses: (will be list/dict)
                            ns_dict[subkey] = None  # Placeholder
                            pending_key = subkey
                            pending_indent = indent
                            pending_target_dict = ns_dict
                    else:
                        # Regular key without dot
                        current_nested_dict[key] = self._parse_yaml_value(value) if value else None
                        if not value:
                            # Nested key might start another level
                            pending_key = key
                            pending_indent = indent
                            pending_target_dict = current_nested_dict
                # Handle nested at root level (ex: primary/node dentro de tests)
                elif current_key and isinstance(data.get(current_key), dict):
                    # Already a dict, just add new key
                    data[current_key][key] = self._parse_yaml_value(value) if value else None
                    if not value:
                        pending_key = key
                        pending_indent = indent
                        pending_target_dict = data[current_key]
                elif current_key and data.get(current_key) is None:
                    # First child of root-level key - it's a dict
                    data[current_key] = {}
                    data[current_key][key] = self._parse_yaml_value(value) if value else None
                    pending_key = None
                    pending_indent = None
                    pending_target_dict = None
                    if not value:
                        pending_key = key
                        pending_indent = indent
                        pending_target_dict = data[current_key]
                # Handle nested dict in list (ex: anchors dentro de unit)
                elif current_dict is not None:
                    if value:
                        # Simple nested value
                        current_dict[key] = self._parse_yaml_value(value)
                        current_nested_dict = None
                        pending_key = None
                        pending_indent = None
                        pending_target_dict = None
                    else:
                        # Nested dict (ex: anchors:)
                        current_dict[key] = {}
                        current_nested_dict = current_dict[key]
                        pending_key = None
                        pending_indent = None
                        pending_target_dict = None
        
        return data
    
    def _parse_yaml_value(self, value: str):
        """Parseia valor YAML (string, number, bool, quoted string)"""
        value = value.strip()
        
        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Boolean
        if value.lower() in ['true', 'yes']:
            return True
        if value.lower() in ['false', 'no']:
            return False
        
        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # String (unquoted)
        return value
    
    def _parse_legacy(self, inv_id: str, section_content: str) -> InvariantSpec:
        """Parser legacy para invariantes sem bloco SPEC"""
        # Extrair status
        status_match = re.search(r'\*\*Status\*\*:\s*(\w+)', section_content)
        status = status_match.group(1) if status_match else 'CONFIRMADA'
        
        # Ignorar invariantes inativas
        if status == 'INATIVA':
            return InvariantSpec(
                id=inv_id,
                status=status,
                test_required=False,
                units=[],
                tests={},
                has_spec=False
            )
        
        # Extrair classe (procurar em múltiplos formatos)
        class_match = re.search(r'\*\*Classe\*\*:\s*([A-F]\d?)', section_content)
        if not class_match:
            class_match = re.search(r'Classe:\s*([A-F]\d?)', section_content)
        class_type = class_match.group(1) if class_match else 'UNKNOWN'
        
        # Extrair escopo
        scope_match = re.search(r'\*\*Escopo\*\*:\s*`?([^`\n]+)`?', section_content)
        scope = scope_match.group(1).strip() if scope_match else ''
        
        # Extrair evidências (constraint names, file:line, operationIds)
        evidence = []
        # Constraints: ck_*, uq_*, fk_*, tr_*, fn_*, idx_* (UNIQUE INDEX)
        evidence.extend(re.findall(r'`((?:ck|uq|fk|tr|fn|ux|idx)_[\w]+)`', section_content))
        # File:line references
        evidence.extend(re.findall(r'`([^`]+\.py:\d+)`', section_content))
        # OperationIds (OpenAPI)
        evidence.extend(re.findall(r'`([a-z_]+_api_v\d_[^`]+)`', section_content))
        
        return InvariantSpec(
            id=inv_id,
            status=status,
            test_required=True,
            units=[],  # Empty for legacy
            tests={},
            has_spec=False,
            class_type=class_type,
            scope=scope,
            evidence=evidence
        )


# ============================================================================
# FILE CLASSIFIER
# ============================================================================

class FileClassifier:
    """Classifica arquivos de teste em principal/suplementar"""
    
    def __init__(self, tests_dir: Path):
        self.tests_dir = tests_dir
    
    def find_test_files(self) -> Dict[str, List[TestFile]]:
        """
        Encontra todos arquivos de teste e agrupa por INV-ID
        
        Returns:
            Dict[inv_id -> List[TestFile]]
        """
        files_by_inv = {}
        
        if not self.tests_dir.exists():
            return files_by_inv
        
        for file_path in self.tests_dir.glob('test_inv_train_*.py'):
            # Extrair INV-ID do nome do arquivo
            # Padrão: test_inv_train_001_*.py ou test_inv_train_001-A_*.py (splits)
            match = re.match(r'test_inv_train_(\d{3}(?:-[A-Z]\d*)?)(?:_.*)?\.py', file_path.name)
            if not match:
                continue
            
            inv_num = match.group(1)
            inv_id = f"INV-TRAIN-{inv_num}"
            
            # Detectar se é runtime suplementar
            is_runtime = '_runtime.py' in file_path.name
            
            test_file = TestFile(
                path=file_path,
                inv_id=inv_id,
                is_runtime=is_runtime
            )
            
            if inv_id not in files_by_inv:
                files_by_inv[inv_id] = []
            files_by_inv[inv_id].append(test_file)
        
        return files_by_inv


# ============================================================================
# AST ANALYZER
# ============================================================================

class ASTAnalyzer(ast.NodeVisitor):
    """Analisa AST de arquivo de teste para detectar padrões e anti-patterns"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.class_name = None
        self.fixtures_used = set()
        self.valid_test_count = 0
        self.invalid_test_count = 0
        self.pytest_raises_exceptions = set()
        self.patterns_found = {
            'pytest_raises_integrity': False,
            'pgcode_structured': False,
            'constraint_structured': False,
            'rollback_called': False,
            'flush_called': False,
            'uuid4_used': False,
            'uses_pg_error_helper': False,  # Helper canônico tests._helpers.pg_error
        }
        self.anti_patterns = []
        self.docstrings = {}
        self.current_function = None
    
    def analyze(self) -> ASTAnalysis:
        """Executa análise AST completa"""
        try:
            content = self.file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(self.file_path))
            self._assign_parents(tree)
            
            # Capturar docstring do módulo
            if ast.get_docstring(tree):
                self.docstrings['module'] = ast.get_docstring(tree)
            
            self.visit(tree)
            
            # Extrair INV-ID do nome do arquivo
            match = re.match(r'test_inv_train_(\d{3})', self.file_path.name)
            inv_id = f"INV-TRAIN-{match.group(1)}" if match else "UNKNOWN"
            
            return ASTAnalysis(
                inv_id=inv_id,
                class_name=self.class_name,
                fixtures_used=self.fixtures_used,
                valid_test_count=self.valid_test_count,
                invalid_test_count=self.invalid_test_count,
                pytest_raises_exceptions=self.pytest_raises_exceptions,
                patterns_found=self.patterns_found.copy(),
                docstrings=self.docstrings.copy(),
                anti_patterns=self.anti_patterns.copy()
            )
        
        except Exception as e:
            raise RuntimeError(f"Failed to parse {self.file_path}: {e}")
    
    def _assign_parents(self, node: ast.AST) -> None:
        """Attach _parent pointers so Constant/keyword checks can be stable."""
        for parent in ast.walk(node):
            for child in ast.iter_child_nodes(parent):
                setattr(child, "_parent", parent)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Detecta classe de teste TestInvTrainXXX"""
        if node.name.startswith('TestInvTrain'):
            self.class_name = node.name
            if ast.get_docstring(node):
                self.docstrings['class'] = ast.get_docstring(node)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Detecta imports, incluindo helper canônico pg_error"""
        if node.module and 'tests._helpers.pg_error' in node.module:
            # from tests._helpers.pg_error import assert_pg_constraint_violation
            for alias in node.names:
                if 'assert_pg_constraint_violation' in alias.name:
                    self.patterns_found['uses_pg_error_helper'] = True
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analisa funcoes sync (inclui helpers) e metodos de teste."""
        self._handle_function_common(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Analisa funcoes async (pytest.mark.asyncio / async def test_*)."""
        self._handle_function_common(node)

    def _handle_function_common(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        """Lógica comum para funções sync e async."""
        prev_function = self.current_function
        self.current_function = node.name
        self._handle_function_node(node)
        self.generic_visit(node)
        self.current_function = prev_function

    def _handle_function_node(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        """Processa nós de função (sync ou async) para fixtures e detecção de testes."""
        # Detectar fixtures usados na assinatura (incluindo args, posonly e kwonly)
        args_obj = getattr(node, "args", None)
        if args_obj:
            all_arg_nodes = []
            if hasattr(args_obj, "args"): all_arg_nodes.extend(args_obj.args)
            if hasattr(args_obj, "posonlyargs"): all_arg_nodes.extend(args_obj.posonlyargs)
            if hasattr(args_obj, "kwonlyargs"): all_arg_nodes.extend(args_obj.kwonlyargs)
            
            for arg in all_arg_nodes:
                if arg.arg in ['async_db', 'auth_client', 'client', 'db']:
                    self.fixtures_used.add(arg.arg)

        # Contar testes validos vs invalidos (por presenca de pytest.raises)
        name = getattr(node, "name", "") or ""
        if name.startswith('test_'):
            has_pytest_raises = self._has_pytest_raises(node)
            if has_pytest_raises:
                self.invalid_test_count += 1
                self.patterns_found['pytest_raises_integrity'] = True
            else:
                self.valid_test_count += 1
    
    def visit_Attribute(self, node: ast.Attribute):
        """Detecta padrões de atributos estruturados"""
        # orig.pgcode (atributo direto)
        if node.attr == 'pgcode':
            self.patterns_found['pgcode_structured'] = True

        # diag.constraint_name (atributo direto)
        if node.attr == 'constraint_name':
            self.patterns_found['constraint_structured'] = True
        
        # rollback()
        if node.attr == 'rollback':
            self.patterns_found['rollback_called'] = True
        
        # flush()
        if node.attr == 'flush':
            self.patterns_found['flush_called'] = True
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detecta chamadas de funções importantes e anti-patterns"""
        func_name = self._get_func_name(node.func)
        
        # Helper canônico: assert_pg_constraint_violation()
        if func_name == 'assert_pg_constraint_violation':
            self.patterns_found['uses_pg_error_helper'] = True
            # Quando usa helper, considera que pgcode e constraint estão sendo verificados
            self.patterns_found['pgcode_structured'] = True
            self.patterns_found['constraint_structured'] = True
        
        # uuid4() usage
        if func_name == 'uuid4':
            self.patterns_found['uuid4_used'] = True

        # getattr(orig, 'pgcode', ...) / getattr(diag, 'constraint_name', ...)
        if func_name == 'getattr' and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            key = node.args[1].value
            if key == 'pgcode':
                self.patterns_found['pgcode_structured'] = True
            if key == 'constraint_name':
                self.patterns_found['constraint_structured'] = True

        # rollback()/flush() calls (more precise than Attribute access)
        if func_name == 'rollback':
            self.patterns_found['rollback_called'] = True
        if func_name == 'flush':
            self.patterns_found['flush_called'] = True
        
        # Anti-pattern: str(exc...), repr(exc...)  (fragil: matches human text)
        if func_name in ['str', 'repr'] and node.args:
            arg0 = node.args[0]
            name0 = self._get_expr_name(arg0)
            if name0 and ('exc' in name0 or 'error' in name0):
                self.anti_patterns.append('string_match_error')
        
        # Anti-pattern: create_engine, sessionmaker
        if func_name in ['create_engine', 'sessionmaker', 'Session']:
            self.anti_patterns.append('engine_creation')
        
        # Anti-pattern: UUID("literal")
        if func_name == 'UUID' and node.args:
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.anti_patterns.append('hardcoded_uuid')

        # DoD-6a: Proibido instanciar Models de lookup tables (ex: Category(...))
        if func_name:
            func_lower = func_name.lower()
            for lookup_table in LOOKUP_TABLES:
                # Match singular form (Category) or plural (Categories)
                if func_lower == lookup_table or func_lower == lookup_table.rstrip('s') or func_lower + 's' == lookup_table:
                    self.anti_patterns.append('lookup_table_insert')
                    break

        self.generic_visit(node)
    
    def visit_Constant(self, node: ast.Constant):
        """Detecta IDs hardcoded"""
        if isinstance(node.value, (int, str)):
            # Detectar padrões como id=123 ou athlete_id="fixed-value"
            parent = getattr(node, '_parent', None)
            if isinstance(parent, ast.keyword):
                if '_id' in parent.arg and isinstance(node.value, (int, str)):
                    if isinstance(node.value, int) or (isinstance(node.value, str) and len(node.value) > 10):
                        self.anti_patterns.append('hardcoded_id')
        
        self.generic_visit(node)
    
    def _has_pytest_raises(self, node: ast.AST) -> bool:
        """Detecta uso de pytest.raises em um método e captura exception types"""
        found = False
        for child in ast.walk(node):
            if isinstance(child, (ast.With, ast.AsyncWith)):
                for item in child.items:
                    ctx = item.context_expr
                    if isinstance(ctx, ast.Call):
                        func_name = self._get_func_name(ctx.func)
                        if func_name and 'raises' in func_name:
                            found = True
                            # Capturar exception type (primeiro argumento)
                            if ctx.args:
                                exc_arg = ctx.args[0]
                                if isinstance(exc_arg, ast.Name):
                                    self.pytest_raises_exceptions.add(exc_arg.id)
                                elif isinstance(exc_arg, ast.Attribute):
                                    self.pytest_raises_exceptions.add(exc_arg.attr)
        return found

    def _get_expr_name(self, node: ast.AST) -> str:
        """Best-effort name for expressions (Name/Attribute chains)."""
        if isinstance(node, ast.Name):
            return node.id.lower()
        if isinstance(node, ast.Attribute):
            base = self._get_expr_name(node.value)
            if base:
                return f"{base}.{node.attr.lower()}"
            return node.attr.lower()
        return ""
    
    def _get_func_name(self, node) -> str:
        """Extrai nome da função de um nó Call"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ''


# ============================================================================
# RULE VALIDATORS
# ============================================================================

class RuleValidator:
    """Valida regras por nível (basic/standard/strict) e classe"""
    
    def __init__(
        self, 
        level: str = 'strict', 
        verbose: bool = False, 
        openapi_ids: Optional[Set[str]] = None,
        openapi_index: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        self.level = level
        self.verbose = verbose
        self.openapi_ids = openapi_ids or set()
        self.openapi_index = openapi_index or {}
    
    def validate_coverage(
        self,
        invariants: List[InvariantSpec],
        files_by_inv: Dict[str, List[TestFile]]
    ) -> List[Violation]:
        """Valida cobertura 1:1 obrigatória"""
        violations = []
        
        for inv in invariants:
            # Skip aliases (test_required=false)
            if inv.is_alias or not inv.test_required:
                # Se é alias, verificar que o canonical existe
                if inv.is_alias and inv.canonical_id:
                    canonical_files = files_by_inv.get(inv.canonical_id, [])
                    canonical_principal = [f for f in canonical_files if f.is_principal]
                    if len(canonical_principal) == 0:
                        violations.append(Violation(
                            inv_id=inv.id,
                            file='',
                            line=0,
                            col=0,
                            level='ERROR',
                            code='ALIAS_CANONICAL_MISSING',
                            message=f'{inv.id} is alias of {inv.canonical_id}, but canonical test not found',
                            action=f'create test for canonical {inv.canonical_id} or fix alias reference'
                        ))
                continue
            
            files = files_by_inv.get(inv.id, [])
            principal_files = [f for f in files if f.is_principal]
            
            if len(principal_files) == 0:
                violations.append(Violation(
                    inv_id=inv.id,
                    file='',
                    line=0,
                    col=0,
                    level='ERROR',
                    code='COVERAGE_MISSING',
                    message=f'no test file for {inv.id}',
                    action=f'create tests/training/invariants/test_inv_train_{inv.id.split("-")[-1].lower()}_*.py'
                ))
            elif len(principal_files) > 1:
                file_list = ', '.join(f.path.name for f in principal_files)
                violations.append(Violation(
                    inv_id=inv.id,
                    file=str(principal_files[0].path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='COVERAGE_DUPLICATE',
                    message=f'multiple main files for {inv.id}: {file_list}',
                    action=f'keep only 1 principal file, move others to *_runtime.py or remove'
                ))
        
        return violations
    
    def validate_dod0(self, analysis: ASTAnalysis, file_path: Path) -> List[Violation]:
        """Valida DoD-0: nomenclatura de classe e métodos"""
        violations = []
        
        if not analysis.class_name:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='DOD0_NO_CLASS',
                message=f'no class TestInvTrain* found',
                action=f'add class TestInvTrain{analysis.inv_id.replace("INV-TRAIN-", "").replace("-", "")}'
            ))
        
        if analysis.valid_test_count == 0 and analysis.invalid_test_count == 0:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='DOD0_NO_TESTS',
                message='no test_* methods found',
                action='add test methods to class'
            ))
        
        return violations
    
    def validate_obligations(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: InvariantSpec,
        verbose: bool = False
    ) -> List[Violation]:
        """Valida Obrigação A e B em modo strict"""
        violations = []
        
        # Apenas em modo strict
        if self.level != 'strict':
            return violations
        
        # Classe F (OpenAPI Contract): Obrigação A não obrigatória, Obrigação B obrigatória
        is_class_f = 'F' in inv.primary_classes
        is_class_c1 = 'C1' in inv.primary_classes  # C1 = feature exposure, não exige Obrigação A/B
        is_class_e1 = 'E1' in inv.primary_classes  # E1 = environment/config constraint, não exige Obrigação A/B
        is_class_b = 'B' in inv.primary_classes  # B = schema documentation, não exige Obrigação A/B
        
        # Selecionar docstring primário (não concatenar todos)
        test_node = inv.tests.get('node') if inv.tests else None
        primary_docstring = pick_primary_docstring(analysis.docstrings, inv.id, test_node)
        
        # Fallback: concatenar todos se não houver primário
        all_docstrings = primary_docstring if primary_docstring else ' '.join(analysis.docstrings.values())
        
        # Obrigação A (não obrigatória para Classe F, C1, E1 e B)
        if not is_class_f and not is_class_c1 and not is_class_e1 and not is_class_b and 'obrigação a' not in all_docstrings.lower():
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='OBLIG_A_MISSING',
                message='docstring missing literal "Obrigação A"',
                action='add Obrigação A section with table.column anchors and keywords (FK, NOT NULL, CHECK)'
            ))
        elif not is_class_f and not is_class_c1 and not is_class_e1 and not is_class_b:
            # Verificar anchors (mínimo 2) - apenas para classes que não sejam F, C1, E1 ou B
            anchors = re.findall(r'\b\w+\.\w+\b', all_docstrings)
            if len(anchors) < 2:
                violations.append(Violation(
                    inv_id=analysis.inv_id,
                    file=str(file_path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='OBLIG_A_INSUFFICIENT_ANCHORS',
                    message=f'found {len(anchors)} anchors, expected >=2',
                    action='add table.column references (ex: training_sessions.status)'
                ))
        
        # Obrigação B (não obrigatória para C1, E1 e B)
        if not is_class_c1 and not is_class_e1 and not is_class_b and 'obrigação b' not in all_docstrings.lower():
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='OBLIG_B_MISSING',
                message='docstring missing literal "Obrigação B"',
                action='add Obrigação B section with SQLSTATE and constraint_name/operationId'
            ))
        else:
            # Determinar quais validações de Obrigação B são obrigatórias baseado na classe
            # Prioridade: C2 > A/B > D (service validation tem precedência sobre DB column documentation)
            db_constraint_classes = {'A'}  # Apenas A (DB constraints com enforcement ativo)
            service_classes = {'C2'}  # C2 = service validation com error_type
            api_classes = {'D'}
            
            # Se tem C2 (service validation), não exigir SQLSTATE mesmo que tenha B
            has_service = any(cls in service_classes for cls in inv.primary_classes)
            has_db_constraint = any(cls in db_constraint_classes for cls in inv.primary_classes)
            has_api = any(cls in api_classes for cls in inv.primary_classes)
            
            # SQLSTATE obrigatório apenas para A (DB constraint), não para B (coluna documenta regra)
            requires_sqlstate = has_db_constraint and not has_service
            requires_error_type = has_service
            requires_operation_id = has_api and not has_service
            
            # Verificar SQLSTATE (23xxx) - APENAS para classes A/B (DB)
            if requires_sqlstate and not re.search(r'23\d{3}', all_docstrings):
                violations.append(Violation(
                    inv_id=analysis.inv_id,
                    file=str(file_path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='OBLIG_B_NO_SQLSTATE',
                    message='Obrigação B missing SQLSTATE (23xxx)',
                    action='add expected SQLSTATE (23514 for CHECK, 23505 for UNIQUE, etc)'
                ))
            
            # PATCH V2: Validar constraint_name e SQLSTATE exatos do SPEC para Classe A
            if has_db_constraint and inv.has_spec:
                # Extrair apenas a seção "Obrigação B" para validação precisa
                obrigacao_b_text = extract_obrigacao_b(all_docstrings)
                
                if not obrigacao_b_text:
                    # Se não conseguir extrair Obrigação B, usar all_docstrings como fallback
                    # (a validação OBLIG_B_MISSING já foi feita acima)
                    obrigacao_b_text = all_docstrings
                
                # Debug output (verbose only, INV-TRAIN-033 only)
                if verbose and inv.id == "INV-TRAIN-033":
                    # Count all_docstrings for diagnostic
                    all_concat = ' '.join(analysis.docstrings.values())
                    obrig_b_count = all_concat.count('Obrigação B')
                    print(f"[DBG] INV-TRAIN-033: obrigacao_b_count_in_all_concat={obrig_b_count}")
                    print(f"[DBG] INV-TRAIN-033: primary_docstring_length={len(primary_docstring)}")
                    print(f"[DBG] INV-TRAIN-033: all_docstrings (after pick)={all_docstrings[:200]!r}...")
                    print(f"[DBG] INV-TRAIN-033: obrigacao_b_text_snip={obrigacao_b_text[:200]!r}")
                
                # Extrair constraints esperados de units com class A e required=True
                expected_constraints = []
                expected_sqlstates = []
                
                for unit in inv.units:
                    if unit.class_type == 'A' and unit.required:
                        # Extrair db.constraint
                        if unit.anchors and 'db' in unit.anchors:
                            db_anchors = unit.anchors['db']
                            if 'constraint' in db_anchors:
                                constraint_name = db_anchors['constraint']
                                if constraint_name:  # não vazio
                                    expected_constraints.append(constraint_name)
                            # Extrair db.sqlstate
                            if 'sqlstate' in db_anchors:
                                sqlstate = db_anchors['sqlstate']
                                if sqlstate:  # não vazio
                                    expected_sqlstates.append(str(sqlstate))
                
                # Debug output (verbose only, INV-TRAIN-033 only)
                if verbose and inv.id == "INV-TRAIN-033":
                    print(f"[DBG] INV-TRAIN-033: expected_constraints={expected_constraints}")
                    print(f"[DBG] INV-TRAIN-033: expected_sqlstates={expected_sqlstates}")
                
                # Validar constraint_name exato dentro da Obrigação B
                for constraint_name in expected_constraints:
                    contains_constraint = constraint_name in obrigacao_b_text
                    if verbose and inv.id == "INV-TRAIN-033":
                        print(f"[DBG] INV-TRAIN-033: contains '{constraint_name}'? {contains_constraint}")
                    if constraint_name not in obrigacao_b_text:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='OBLIG_B_NO_CONSTRAINT_NAME',
                            message=f'Obrigação B missing constraint_name from SPEC: {constraint_name}',
                            action=f'add constraint_name ({constraint_name}) to Obrigação B'
                        ))
                
                # Validar SQLSTATE exato dentro da Obrigação B
                for sqlstate in expected_sqlstates:
                    contains_sqlstate = sqlstate in obrigacao_b_text
                    if verbose and inv.id == "INV-TRAIN-033":
                        print(f"[DBG] INV-TRAIN-033: contains SQLSTATE '{sqlstate}'? {contains_sqlstate}")
                    
                    if sqlstate not in obrigacao_b_text:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='OBLIG_B_SQLSTATE_MISMATCH',
                            message=f'Obrigação B missing exact SQLSTATE from SPEC: {sqlstate}',
                            action=f'add SQLSTATE {sqlstate} to Obrigação B (not just 23xxx pattern)'
                        ))
            
            # Verificar error_type (ValidationError, PermissionError) - para classes C1/C2 (Service)
            if requires_error_type:
                has_error_type = bool(re.search(r'ValidationError|PermissionError|BusinessError', all_docstrings, re.IGNORECASE))
                if not has_error_type:
                    violations.append(Violation(
                        inv_id=analysis.inv_id,
                        file=str(file_path),
                        line=0,
                        col=0,
                        level='ERROR',
                        code='OBLIG_B_NO_ERROR_TYPE',
                        message='Obrigação B missing error_type (ex: ValidationError)',
                        action='add error_type reference to Obrigação B (ValidationError, PermissionError, etc)'
                    ))
            
            # Verificar símbolo (constraint_name ou operationId)
            has_constraint = bool(re.search(r'(?:ck|uq|fk|tr|fn|ux|idx)_\w+', all_docstrings))
            has_operation_id = bool(re.search(r'\w+_api_v\d', all_docstrings))

            # constraint_name obrigatório para DB (A/B), operationId obrigatório para API (D)
            if requires_sqlstate and not has_constraint:
                violations.append(Violation(
                    inv_id=analysis.inv_id,
                    file=str(file_path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='OBLIG_B_NO_CONSTRAINT',
                    message='Obrigação B missing constraint_name (ex: ck_*, uq_*, idx_*)',
                    action='add constraint_name reference (ex: ck_training_sessions_dates, idx_*)'
                ))
            
            if requires_operation_id and not has_operation_id:
                violations.append(Violation(
                    inv_id=analysis.inv_id,
                    file=str(file_path),
                    line=0,
                    col=0,
                    level='ERROR',
                    code='OBLIG_B_NO_OPERATION_ID',
                    message='Obrigação B missing operationId',
                    action='add operationId reference (ex: create_training_session_api_v1)'
                ))
        
        return violations
    
    def validate_class_a(
        self,
        analysis: ASTAnalysis,
        file_path: Path
    ) -> List[Violation]:
        """Valida regras de Classe A (DB constraint)"""
        violations = []
        
        # Mínimo de testes válidos e inválidos
        if analysis.valid_test_count < 1:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_MIN_VALID',
                message=f'found {analysis.valid_test_count} valid tests, expected >=1',
                action='add test_valid_case__* method without pytest.raises'
            ))
        
        if analysis.invalid_test_count < 2:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_MIN_INVALID',
                message=f'found {analysis.invalid_test_count} invalid tests, expected >=2',
                action='add test_invalid_case_N__* methods with pytest.raises(IntegrityError)'
            ))
        
        # Requer async_db
        if 'async_db' not in analysis.fixtures_used:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_REQUIRES_ASYNC_DB',
                message='Classe A requires async_db fixture',
                action='add async_db parameter to test methods'
            ))
        
        # Requer SQLSTATE estruturado (ou helper canônico)
        if not analysis.patterns_found['pgcode_structured'] and not analysis.patterns_found['uses_pg_error_helper']:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_REQUIRES_PGCODE_ATTR',
                message='use orig.pgcode or assert_pg_constraint_violation helper',
                action='replace string matching with: orig = exc.value.orig; assert orig.pgcode == "23514" OR use: from tests._helpers.pg_error import assert_pg_constraint_violation'
            ))
        
        # Requer constraint_name estruturado (ou helper canônico)
        if not analysis.patterns_found['constraint_structured'] and not analysis.patterns_found['uses_pg_error_helper']:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_REQUIRES_CONSTRAINT_ATTR',
                message='use diag.constraint_name or assert_pg_constraint_violation helper',
                action='add: diag = exc.value.orig.diag; assert diag.constraint_name == "ck_*" OR use: from tests._helpers.pg_error import assert_pg_constraint_violation'
            ))
        
        # Requer rollback
        if not analysis.patterns_found['rollback_called']:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_REQUIRES_ROLLBACK',
                message='add await async_db.rollback() after IntegrityError',
                action='add rollback after pytest.raises block'
            ))
        
        # Proibir string matching
        if 'string_match_error' in analysis.anti_patterns:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='A_FORBIDS_STRING_MATCH',
                message='remove str(exc) from assert',
                action='use structured attributes: orig.pgcode, diag.constraint_name'
            ))
        
        # Anti-regressão: se usa helper, proibir acesso direto a orig.diag/orig.__cause__
        # (WARNING apenas, para facilitar migração gradual)
        if analysis.patterns_found['uses_pg_error_helper']:
            # Ler o arquivo para verificar se há uso direto de orig.diag ou orig.__cause__
            content = file_path.read_text(encoding='utf-8')
            if 'orig.diag' in content or 'orig.__cause__' in content:
                violations.append(Violation(
                    inv_id=analysis.inv_id,
                    file=str(file_path),
                    line=0,
                    col=0,
                    level='WARNING',
                    code='A_HELPER_NO_DIRECT_ACCESS',
                    message='when using assert_pg_constraint_violation helper, avoid direct access to orig.diag or orig.__cause__',
                    action='remove manual constraint checks, rely on helper'
                ))
        
        return violations
    
    def validate_class_b(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe B (Schema documentation)"""
        violations = []
        
        # Obter Backend root para encontrar schema.sql
        current = file_path
        while current.parent != current:
            if current.name == 'tests':
                backend_root = current.parent
                break
            current = current.parent
        else:
            backend_root = file_path.parent.parent.parent.parent  # fallback (4x parent)
        
        # Localizar schema.sql em docs/_generated/
        schema_path = backend_root / "docs" / "_generated" / "schema.sql"
        
        if not schema_path.exists():
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='B_SCHEMA_NOT_FOUND',
                message='schema.sql not found in alembic/ or backend root',
                action='ensure schema.sql exists'
            ))
            return violations
        
        schema_content = schema_path.read_text(encoding='utf-8')
        
        # Validar anchors obrigatórios no SPEC
        if inv and inv.units:
            for unit in inv.units:
                if unit.class_type == 'B' and unit.required:
                    if not unit.anchors or 'db' not in unit.anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='B_MISSING_ANCHOR',
                            message='Class B requires db.* anchors in SPEC',
                            action='add db.table, db.column, db.comment to SPEC'
                        ))
                        continue
                    
                    db_anchors = unit.anchors['db']
                    table_name = db_anchors.get('table')

                    # Detectar modo: B1 (column+comment) ou B2 (trigger+function)
                    has_b1_anchors = 'column' in db_anchors and 'comment' in db_anchors
                    has_b2_anchors = 'trigger' in db_anchors and 'function' in db_anchors

                    # Validar que é B1 ou B2 (não ambos vazios)
                    if not has_b1_anchors and not has_b2_anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='B_ANCHORS_INVALID',
                            message='Class B requires either B1 (table+column+comment) or B2 (table+trigger+function) anchors',
                            action='add db.column+db.comment (B1) OR db.trigger+db.function (B2) to SPEC'
                        ))
                        continue

                    # Validar db.table obrigatório para ambos os modos
                    if not table_name:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='B_MISSING_ANCHOR',
                            message='Missing required db.table anchor',
                            action='add db.table to SPEC'
                        ))
                        continue

                    # Validar que table existe no schema
                    table_pattern = rf'CREATE\s+TABLE\s+(public\.)?{re.escape(table_name)}\b'
                    if not re.search(table_pattern, schema_content, re.IGNORECASE | re.MULTILINE):
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='B_TABLE_NOT_FOUND',
                            message=f'db.table not found in schema.sql: {table_name}',
                            action=f'verify table exists in schema.sql or fix SPEC'
                        ))
                        continue

                    # ========== MODO B1: column+comment ==========
                    if has_b1_anchors:
                        column_name = db_anchors.get('column')
                        expected_comment = db_anchors.get('comment')

                        # Validar que column existe na table
                        if table_name and column_name:
                            table_def_pattern = rf'CREATE\s+TABLE\s+(public\.)?{re.escape(table_name)}\s*\([^;]+;'
                            table_match = re.search(table_def_pattern, schema_content, re.IGNORECASE | re.DOTALL)

                            if table_match:
                                table_definition = table_match.group(0)
                                column_pattern = rf'\b{re.escape(column_name)}\b'
                                if not re.search(column_pattern, table_definition, re.IGNORECASE):
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='B_COLUMN_NOT_FOUND',
                                        message=f'db.column not found in table {table_name}: {column_name}',
                                        action=f'verify column exists in schema.sql or fix SPEC'
                                    ))
                                    continue

                        # Validar COMMENT ON COLUMN
                        if table_name and column_name and expected_comment:
                            comment_pattern = rf"COMMENT\s+ON\s+COLUMN\s+(?:public\.)?{re.escape(table_name)}\.{re.escape(column_name)}\s+IS\s+'([^']+)';"
                            comment_match = re.search(comment_pattern, schema_content, re.IGNORECASE | re.DOTALL)

                            if not comment_match:
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='B_COMMENT_NOT_FOUND',
                                    message=f'COMMENT ON COLUMN not found for {table_name}.{column_name}',
                                    action=f'add COMMENT ON COLUMN {table_name}.{column_name} in schema.sql'
                                ))
                            else:
                                actual_comment = comment_match.group(1)
                                if expected_comment.lower() not in actual_comment.lower():
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='B_COMMENT_MISMATCH',
                                        message=f'Comment mismatch for {table_name}.{column_name}: expected substring "{expected_comment}" not found in "{actual_comment}"',
                                        action=f'update schema.sql comment to include "{expected_comment}" or fix SPEC'
                                    ))

                    # ========== MODO B2: trigger+function ==========
                    elif has_b2_anchors:
                        trigger_name = db_anchors.get('trigger')
                        function_name = db_anchors.get('function')

                        # (B2-1) Validar que trigger existe no schema
                        trigger_pattern = rf'CREATE\s+TRIGGER\s+{re.escape(trigger_name)}\b'
                        trigger_match = re.search(trigger_pattern, schema_content, re.IGNORECASE | re.MULTILINE)
                        if not trigger_match:
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='B_TRIGGER_NOT_FOUND',
                                message=f'CREATE TRIGGER not found in schema.sql: {trigger_name}',
                                action=f'verify trigger {trigger_name} exists in schema.sql or fix SPEC'
                            ))
                            continue

                        # (B2-2) Validar que function existe no schema
                        function_pattern = rf'CREATE\s+FUNCTION\s+(public\.)?{re.escape(function_name)}\s*\('
                        if not re.search(function_pattern, schema_content, re.IGNORECASE | re.MULTILINE):
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='B_FUNCTION_NOT_FOUND',
                                message=f'CREATE FUNCTION not found in schema.sql: {function_name}',
                                action=f'verify function {function_name} exists in schema.sql or fix SPEC'
                            ))
                            continue

                        # (B2-3) Validar binding: trigger ON table EXECUTE FUNCTION fn
                        trigger_block_pattern = rf'CREATE\s+TRIGGER\s+{re.escape(trigger_name)}\s+[^;]+;'
                        trigger_block_match = re.search(trigger_block_pattern, schema_content, re.IGNORECASE | re.DOTALL)

                        if trigger_block_match:
                            trigger_block = trigger_block_match.group(0)

                            # Verificar ON public.table
                            on_table_pattern = rf'ON\s+(public\.)?{re.escape(table_name)}\b'
                            if not re.search(on_table_pattern, trigger_block, re.IGNORECASE):
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='B_BINDING_NOT_FOUND',
                                    message=f'Trigger {trigger_name} not bound to table {table_name}',
                                    action=f'verify trigger {trigger_name} is ON {table_name} in schema.sql or fix SPEC'
                                ))
                                continue

                            # Verificar EXECUTE FUNCTION public.fn
                            execute_pattern = rf'EXECUTE\s+(FUNCTION|PROCEDURE)\s+(public\.)?{re.escape(function_name)}\s*\('
                            if not re.search(execute_pattern, trigger_block, re.IGNORECASE):
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='B_BINDING_NOT_FOUND',
                                    message=f'Trigger {trigger_name} does not EXECUTE FUNCTION {function_name}',
                                    action=f'verify trigger {trigger_name} executes {function_name} in schema.sql or fix SPEC'
                                ))
        
        return violations
    
    def validate_class_c1(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe C1 (Feature exposure via router/service)"""
        violations = []
        
        # Obter Backend root
        current = file_path
        while current.parent != current:
            if current.name == 'tests':
                backend_root = current.parent
                break
            current = current.parent
        else:
            backend_root = file_path.parent.parent.parent  # fallback
        
        # Validar anchors obrigatórios no SPEC
        if inv and inv.units:
            for unit in inv.units:
                if unit.class_type == 'C1' and unit.required:
                    if not unit.anchors or 'code' not in unit.anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='C1_MISSING_ANCHOR',
                            message='Class C1 requires code.* anchors in SPEC',
                            action='add code.router_file and code.router_symbols to SPEC'
                        ))
                        continue
                    
                    code_anchors = unit.anchors['code']
                    
                    # (C1-1) Validar router_file obrigatório
                    if 'router_file' not in code_anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='C1_MISSING_ANCHOR',
                            message='Class C1 requires code.router_file in SPEC',
                            action='add code.router_file to SPEC anchors'
                        ))
                        continue
                    
                    # (C1-2) Validar que router_file existe
                    router_file = code_anchors.get('router_file')
                    if router_file:
                        router_file_path = backend_root / router_file
                        if not router_file_path.exists():
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='C1_ROUTER_FILE_NOT_FOUND',
                                message=f'code.router_file not found: {router_file}',
                                action=f'verify file exists: {router_file_path}'
                            ))
                        else:
                            # (C1-3) Validar router_symbols (se houver)
                            router_symbols = code_anchors.get('router_symbols', [])
                            if isinstance(router_symbols, str):
                                router_symbols = [router_symbols]
                            
                            if router_symbols:
                                router_content = router_file_path.read_text(encoding='utf-8')
                                for symbol in router_symbols:
                                    # Buscar "def symbol" ou "async def symbol"
                                    pattern = rf'\b(?:async\s+)?def\s+{re.escape(symbol)}\s*\('
                                    if not re.search(pattern, router_content):
                                        violations.append(Violation(
                                            inv_id=analysis.inv_id,
                                            file=str(file_path),
                                            line=0,
                                            col=0,
                                            level='ERROR',
                                            code='C1_ROUTER_SYMBOL_NOT_FOUND',
                                            message=f'code.router_symbol not found in {router_file}: {symbol}',
                                            action=f'add function/handler {symbol} to router or fix SPEC'
                                        ))
                    
                    # (C1-4) Validar service_file e service_symbol (se houver)
                    service_file = code_anchors.get('service_file')
                    if service_file:
                        service_file_path = backend_root / service_file
                        if not service_file_path.exists():
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='C1_SERVICE_FILE_NOT_FOUND',
                                message=f'code.service_file not found: {service_file}',
                                action=f'verify file exists: {service_file_path}'
                            ))
                        else:
                            service_symbol = code_anchors.get('service_symbol')
                            if service_symbol:
                                service_content = service_file_path.read_text(encoding='utf-8')
                                # Buscar "class Symbol" ou "def symbol"
                                class_pattern = rf'\bclass\s+{re.escape(service_symbol)}\b'
                                def_pattern = rf'\b(?:async\s+)?def\s+{re.escape(service_symbol)}\s*\('
                                
                                if not (re.search(class_pattern, service_content) or 
                                       re.search(def_pattern, service_content)):
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='C1_SERVICE_SYMBOL_NOT_FOUND',
                                        message=f'code.service_symbol not found in {service_file}: {service_symbol}',
                                        action=f'add class/function {service_symbol} to service or fix SPEC'
                                    ))
        
        # (C1-5) Classe C1 pode usar HTTP fixtures (router exposure) mas não é obrigatório
        # Não forçar client/auth_client pois C1 pode ser testado via filesystem ou imports
        
        return violations
    
    def validate_class_c2(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe C2 (Service validation)"""
        violations = []
        
        # Obter Backend root para verificar code.file
        # file_path: C:\HB TRACK\Hb Track - Backend\tests\training\invariants\test_*.py
        # backend_root: C:\HB TRACK\Hb Track - Backend
        current = file_path
        while current.parent != current:
            if current.name == 'tests':
                backend_root = current.parent
                break
            current = current.parent
        else:
            backend_root = file_path.parent.parent.parent  # fallback
        
        # Validar anchors obrigatórios no SPEC
        if inv and inv.units:
            for unit in inv.units:
                if unit.class_type == 'C2' and unit.required:
                    if not unit.anchors or 'code' not in unit.anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='C2_MISSING_ANCHOR',
                            message='Class C2 requires code.* anchors in SPEC',
                            action='add code.file, code.symbol, code.lines, code.error_type to SPEC'
                        ))
                        continue
                    
                    code_anchors = unit.anchors['code']
                    
                    # Validar presença de anchors obrigatórios
                    required_anchors = ['file', 'symbol', 'lines', 'error_type']
                    missing = [a for a in required_anchors if a not in code_anchors]
                    if missing:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='C2_MISSING_ANCHOR',
                            message=f'Missing required code.* anchors: {missing}',
                            action=f'add {", ".join(missing)} to SPEC code anchors'
                        ))
                        continue
                    
                    # (C2-2) Validar que code.file existe
                    code_file = code_anchors.get('file')
                    if code_file:
                        code_file_path = backend_root / code_file
                        if not code_file_path.exists():
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='C2_CODE_FILE_NOT_FOUND',
                                message=f'code.file not found: {code_file}',
                                action=f'verify file exists: {code_file_path}'
                            ))
                    
                    # (C2-4) Validar pytest.raises com error_type do SPEC
                    error_type = code_anchors.get('error_type')
                    if error_type:
                        if error_type not in analysis.pytest_raises_exceptions:
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='C2_MISSING_PYTEST_RAISES',
                                message=f'Class C2 requires pytest.raises({error_type}) test',
                                action=f'add test_invalid_case with pytest.raises({error_type})'
                            ))
        
        # (C2-3) Proibir HTTP fixtures (típicas de Router/Contract)
        forbidden_fixtures = {'client', 'auth_client'}
        used_forbidden = forbidden_fixtures.intersection(analysis.fixtures_used)
        if used_forbidden:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='C2_FORBIDS_HTTP_FIXTURES',
                message=f'Class C2 forbids HTTP client fixtures: {used_forbidden}',
                action='remove client/auth_client fixtures (C2 tests service layer, not HTTP)'
            ))
        
        # (C2-5) Exigir pelo menos 1 caso válido
        if analysis.valid_test_count == 0:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='C2_MISSING_VALID_CASE',
                message='Class C2 requires at least 1 valid test case',
                action='add test_valid_case method without pytest.raises'
            ))
        
        return violations
    
    def validate_class_e1(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe E1 (Environment/Config constraint)"""
        violations = []
        
        # Obter Backend root
        current = file_path
        while current.parent != current:
            if current.name == 'tests':
                backend_root = current.parent
                break
            current = current.parent
        else:
            backend_root = file_path.parent.parent.parent  # fallback
        
        # Validar anchors obrigatórios no SPEC
        if inv and inv.units:
            for unit in inv.units:
                if unit.class_type == 'E1' and unit.required:
                    if not unit.anchors or 'code' not in unit.anchors:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='E1_MISSING_ANCHOR',
                            message='Class E1 requires code.* anchors in SPEC',
                            action='add code.file, code.function, code.pattern to SPEC'
                        ))
                        continue
                    
                    code_anchors = unit.anchors['code']
                    
                    # (E1-1) Validar anchors obrigatórios
                    required_anchors = ['file', 'function', 'pattern']
                    missing = [a for a in required_anchors if a not in code_anchors]
                    if missing:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='E1_MISSING_ANCHOR',
                            message=f'Missing required code.* anchors: {missing}',
                            action=f'add {', '.join(missing)} to SPEC code anchors'
                        ))
                        continue
                    
                    # (E1-2) Validar que code.file existe
                    code_file = code_anchors.get('file')
                    if code_file:
                        code_file_path = backend_root / code_file
                        if not code_file_path.exists():
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='E1_CODE_FILE_NOT_FOUND',
                                message=f'code.file not found: {code_file}',
                                action=f'verify file exists: {code_file_path}'
                            ))
                        else:
                            code_content = code_file_path.read_text(encoding='utf-8')
                            
                            # (E1-3) Validar code.function
                            code_function = code_anchors.get('function')
                            if code_function:
                                # Buscar "def function" ou "async def function"
                                function_pattern = rf'^(?:async\s+)?def\s+{re.escape(code_function)}\b'
                                if not re.search(function_pattern, code_content, re.MULTILINE):
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='E1_FUNCTION_NOT_FOUND',
                                        message=f'code.function not found in {code_file}: {code_function}',
                                        action=f'verify function exists in file or fix SPEC'
                                    ))
                            
                            # (E1-4) Validar code.pattern (substring simples)
                            code_pattern = code_anchors.get('pattern')
                            if code_pattern:
                                if code_pattern not in code_content:
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='E1_PATTERN_NOT_FOUND',
                                        message=f'code.pattern not found in {code_file}: {code_pattern}',
                                        action=f'verify pattern exists in file or fix SPEC'
                                    ))
        
        # (E1-5) Proibir DB e HTTP fixtures (E1 é code/ops-only)
        forbidden_fixtures = {'async_db', 'db', 'client', 'auth_client'}
        used_forbidden = forbidden_fixtures.intersection(analysis.fixtures_used)
        if used_forbidden:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='E1_FORBIDS_DB_OR_HTTP_FIXTURES',
                message=f'Class E1 forbids DB/HTTP fixtures: {used_forbidden}',
                action='remove DB/HTTP fixtures (E1 tests are code/ops-only)'
            ))
        
        return violations
    
    def validate_class_f(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe F (OpenAPI Contract) com coerência SPEC ↔ OpenAPI"""
        violations = []
        
        # Classe F não deve usar fixtures de DB
        forbidden_fixtures = {'db', 'async_db'}
        used_forbidden = forbidden_fixtures.intersection(analysis.fixtures_used)
        if used_forbidden:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='F_FORBIDS_DB_FIXTURES',
                message=f'Classe F forbids DB fixtures: {used_forbidden}',
                action='remove DB fixtures (contract tests validate against openapi.json only)'
            ))
        
        # Validar coerência SPEC ↔ OpenAPI (F1-F4)
        if inv and self.openapi_index and inv.units:
            for unit in inv.units:
                if unit.anchors and 'api' in unit.anchors:
                    api_anchors = unit.anchors['api']
                    
                    # Extrair anchors do SPEC
                    op_id = api_anchors.get('operation_id')
                    expected_method = api_anchors.get('method', '').upper()
                    expected_path = api_anchors.get('path', '')
                    expected_responses = api_anchors.get('responses', [])
                    expected_security = api_anchors.get('security')  # "none", "bearer", []
                    
                    if not op_id:
                        continue
                    
                    # Normalizar operation_id para lista
                    if isinstance(op_id, str):
                        op_ids_to_check = [op_id]
                    else:
                        op_ids_to_check = op_id
                    
                    for oid in op_ids_to_check:
                        # (F1) Validar que operationId existe no OpenAPI
                        if oid not in self.openapi_index:
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='F_OPERATION_ID_NOT_IN_OPENAPI',
                                message=f'operationId not found in openapi.json: {oid}',
                                action='use exact operationId from openapi.json (docs/_generated/openapi.json)'
                            ))
                            continue
                        
                        openapi_entry = self.openapi_index[oid]
                        
                        # (F2) Validar method+path
                        openapi_method = openapi_entry['method']
                        openapi_path = openapi_entry['path']
                        
                        if expected_method and expected_method != openapi_method:
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='F_METHOD_MISMATCH',
                                message=f'method mismatch for {oid}: SPEC={expected_method}, OpenAPI={openapi_method}',
                                action=f'update SPEC api.method to "{openapi_method.lower()}"'
                            ))
                        
                        if expected_path and expected_path != openapi_path:
                            violations.append(Violation(
                                inv_id=analysis.inv_id,
                                file=str(file_path),
                                line=0,
                                col=0,
                                level='ERROR',
                                code='F_PATH_MISMATCH',
                                message=f'path mismatch for {oid}: SPEC={expected_path}, OpenAPI={openapi_path}',
                                action=f'update SPEC api.path to "{openapi_path}"'
                            ))
                        
                        # (F3) Validar responses (bidirecional: extras e missing)
                        if expected_responses is not None:
                            # Normalizar tudo para strings
                            if isinstance(expected_responses, list):
                                expected = set(str(x) for x in expected_responses)
                            else:
                                expected = set()
                            
                            openapi_responses = openapi_entry['responses']
                            # Remover 'default' se existir (não é código específico)
                            openapi_clean = openapi_responses - {'default'}
                            
                            # Verbose logging (genérico para qualquer INV Classe F)
                            if self.verbose:
                                print(f"[F3] {oid}: expected_responses={sorted(expected)}, openapi_responses={sorted(openapi_clean)}")
                            
                            # Validar: SPEC vazio é erro
                            if len(expected) == 0:
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='F_RESPONSES_EMPTY',
                                    message=f'api.responses is empty for {oid}. OpenAPI has: {sorted(openapi_clean)}',
                                    action=f'add response codes to SPEC api.responses: {sorted(openapi_clean)}'
                                ))
                            else:
                                # Validar: códigos extras no SPEC que não existem no OpenAPI
                                extras = expected - openapi_clean
                                if extras:
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='F_RESPONSES_NOT_IN_OPENAPI',
                                        message=f'responses in SPEC not found in OpenAPI for {oid}: {sorted(extras)}. OpenAPI has: {sorted(openapi_clean)}',
                                        action=f'remove invalid response codes from SPEC: {sorted(extras)}'
                                    ))
                                
                                # Validar: códigos no OpenAPI que faltam no SPEC
                                missing = openapi_clean - expected
                                if missing:
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='F_RESPONSES_MISSING_FROM_SPEC',
                                        message=f'OpenAPI has response codes not in SPEC for {oid}: {sorted(missing)}. SPEC has: {sorted(expected)}',
                                        action=f'add missing response codes to SPEC: {sorted(missing)}'
                                    ))
                        
                        # (F4) Validar security (SPEC ↔ OpenAPI)
                        if expected_security is not None:
                            # Normalizar expected_security para set de schemes
                            if isinstance(expected_security, list):
                                expected_schemes = set(expected_security)
                            elif expected_security == "none" or expected_security == "":
                                expected_schemes = set()
                            else:
                                expected_schemes = {expected_security}
                            
                            # Obter schemes do OpenAPI
                            openapi_schemes = openapi_entry.get('security_schemes', set())
                            
                            # Verbose logging
                            if self.verbose:
                                print(f"[F4] {oid}: expected_security={sorted(expected_schemes)}, openapi_security={sorted(openapi_schemes)}")
                            
                            # Validar: OpenAPI exige security mas SPEC está vazio
                            if len(openapi_schemes) > 0 and len(expected_schemes) == 0:
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='F_SECURITY_MISSING_FROM_SPEC',
                                    message=f'OpenAPI requires security for {oid}: {sorted(openapi_schemes)}, but SPEC has none',
                                    action=f'add api.security to SPEC: {sorted(openapi_schemes)}'
                                ))
                            # Validar: SPEC tem scheme que não existe no OpenAPI
                            elif len(expected_schemes) > 0 and len(openapi_schemes) == 0:
                                violations.append(Violation(
                                    inv_id=analysis.inv_id,
                                    file=str(file_path),
                                    line=0,
                                    col=0,
                                    level='ERROR',
                                    code='F_SECURITY_NOT_IN_OPENAPI',
                                    message=f'SPEC declares security for {oid}: {sorted(expected_schemes)}, but OpenAPI has none',
                                    action='remove api.security from SPEC or check OpenAPI security definition'
                                ))
                            # Validar: mismatch de schemes
                            elif expected_schemes != openapi_schemes:
                                extras = expected_schemes - openapi_schemes
                                missing = openapi_schemes - expected_schemes
                                if extras or missing:
                                    msg_parts = []
                                    if extras:
                                        msg_parts.append(f"extra in SPEC: {sorted(extras)}")
                                    if missing:
                                        msg_parts.append(f"missing from SPEC: {sorted(missing)}")
                                    violations.append(Violation(
                                        inv_id=analysis.inv_id,
                                        file=str(file_path),
                                        line=0,
                                        col=0,
                                        level='ERROR',
                                        code='F_SECURITY_MISMATCH',
                                        message=f'Security mismatch for {oid}: {", ".join(msg_parts)}. OpenAPI: {sorted(openapi_schemes)}, SPEC: {sorted(expected_schemes)}',
                                        action=f'update SPEC api.security to match OpenAPI: {sorted(openapi_schemes)}'
                                    ))
        
        return violations
    
    def validate_class_d(
        self,
        analysis: ASTAnalysis,
        file_path: Path,
        inv: Optional['InvariantSpec'] = None
    ) -> List[Violation]:
        """Valida regras de Classe D (Router/RBAC)"""
        violations = []
        
        total_tests = analysis.valid_test_count + analysis.invalid_test_count
        if total_tests < 3:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='D_MIN_TESTS',
                message=f'found {total_tests} tests, expected >=3 (401/403/200)',
                action='add tests: test_without_auth_401, test_without_permission_403, test_with_permission_200'
            ))
        
        # Requer auth_client ou client
        if not ('auth_client' in analysis.fixtures_used or 'client' in analysis.fixtures_used):
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='D_REQUIRES_CLIENT',
                message='Classe D requires auth_client or client fixture',
                action='add auth_client or client parameter to test methods'
            ))
        
        # Proibir async_db
        if 'async_db' in analysis.fixtures_used:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='D_FORBIDS_ASYNC_DB',
                message='Classe D forbids async_db fixture',
                action='remove async_db fixture (Router tests should not access DB directly)'
            ))
        
        # Validar operationId contra OpenAPI spec (se inv e openapi_ids disponíveis)
        if inv and self.openapi_ids and inv.units:
            # Buscar operation_id em todos os units
            expected_operation_ids = []
            for unit in inv.units:
                if unit.anchors and 'api' in unit.anchors:
                    api_anchors = unit.anchors['api']
                    op_id = api_anchors.get('operation_id')
                    if op_id:
                        # Normalizar para lista
                        if isinstance(op_id, str):
                            expected_operation_ids.append(op_id)
                        elif isinstance(op_id, list):
                            expected_operation_ids.extend(op_id)
            
            if expected_operation_ids:
                # Extrair operationIds do docstring
                module_docstring = analysis.docstrings.get('module', '')
                class_docstring = analysis.docstrings.get('class', '')
                all_docstrings = module_docstring + ' ' + class_docstring
                obrigacao_b_text = extract_obrigacao_b(all_docstrings)
                
                # Procurar padrões de operationId no docstring
                found_operation_ids = re.findall(r'\w+_api_v\d+[_\w]*', obrigacao_b_text)
                
                # Validar se algum operationId encontrado existe no OpenAPI
                for found_id in found_operation_ids:
                    if found_id not in self.openapi_ids:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=0,
                            col=0,
                            level='ERROR',
                            code='D_OPERATION_ID_NOT_IN_OPENAPI',
                            message=f'operationId not found in openapi.json: {found_id}',
                            action='use exact operationId from openapi.json (docs/_generated/openapi.json)'
                        ))
        
        return violations
    
    def validate_anti_patterns(
        self,
        analysis: ASTAnalysis,
        file_path: Path
    ) -> List[Violation]:
        """Valida anti-patterns críticos (todos os arquivos)"""
        violations = []
        
        if 'engine_creation' in analysis.anti_patterns:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='ENGINE_CREATION',
                message='forbidden: create_engine/sessionmaker/Session',
                action='remove custom engine creation, use async_db fixture'
            ))
        
        if 'hardcoded_uuid' in analysis.anti_patterns:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='HARDCODED_UUID',
                message='forbidden: UUID("literal")',
                action='replace with uuid4() for dynamic generation'
            ))
        
        if 'hardcoded_id' in analysis.anti_patterns:
            violations.append(Violation(
                inv_id=analysis.inv_id,
                file=str(file_path),
                line=0,
                col=0,
                level='ERROR',
                code='HARDCODED_ID',
                message='forbidden: hardcoded IDs (id=123, athlete_id="fixed")',
                action='use uuid4() or factory for dynamic ID generation'
            ))
        
        return violations


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Gera relatórios JSON e TXT"""
    
    @staticmethod
    def generate(
        violations: List[Violation],
        level: str,
        total_invariants: int,
        covered_invariants: int
    ) -> ValidationReport:
        """Gera relatório completo"""
        # Sort violations deterministically: (inv_id, file, line, col, code)
        # This ensures consistent output across runs for the same violations
        sorted_violations = sorted(
            violations,
            key=lambda v: (v.inv_id, v.file, v.line, v.col, v.code)
        )
        
        error_count = sum(1 for v in sorted_violations if v.level == 'ERROR')
        warn_count = sum(1 for v in sorted_violations if v.level == 'WARN')
        
        return ValidationReport(
            pass_status=(error_count == 0),
            level=level,
            timestamp=datetime.now().isoformat(),
            summary={
                'total_invariants': total_invariants,
                'covered': covered_invariants,
                'error_count': error_count,
                'warning_count': warn_count
            },
            violations=sorted_violations
        )
    
    @staticmethod
    def write_json(report: ValidationReport, path: Path):
        """Escreve relatório JSON"""
        data = {
            'pass': report.pass_status,
            'level': report.level,
            'timestamp': report.timestamp,
            'summary': report.summary,
            'violations': [
                {
                    'inv_id': v.inv_id,
                    'file': v.file,
                    'line': v.line,
                    'col': v.col,
                    'level': v.level,
                    'code': v.code,
                    'message': v.message,
                    'action': v.action
                }
                for v in report.violations
            ]
        }
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    @staticmethod
    def write_txt(report: ValidationReport, path: Path):
        """Escreve relatório TXT legível"""
        lines = []
        lines.append("=" * 80)
        lines.append("VALIDATION REPORT: verify_invariants_tests.py")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Level: {report.level}")
        lines.append(f"Status: {'✅ PASS' if report.pass_status else '❌ FAIL'}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY:")
        lines.append(f"  Total Invariants: {report.summary['total_invariants']}")
        lines.append(f"  Covered: {report.summary['covered']}")
        lines.append(f"  Errors: {report.summary['error_count']}")
        lines.append(f"  Warnings: {report.summary['warning_count']}")
        lines.append("")
        
        # Group violations by INV-ID
        if report.violations:
            lines.append("VIOLATIONS:")
            lines.append("-" * 80)
            
            violations_by_inv = {}
            for v in report.violations:
                if v.inv_id not in violations_by_inv:
                    violations_by_inv[v.inv_id] = []
                violations_by_inv[v.inv_id].append(v)
            
            for inv_id in sorted(violations_by_inv.keys()):
                lines.append(f"\n{inv_id}:")
                for v in violations_by_inv[inv_id]:
                    icon = "❌" if v.level == "ERROR" else "⚠️"
                    location = f"{v.file}:{v.line}:{v.col}" if v.file else "(coverage)"
                    lines.append(f"  {icon} {location}: {v.level} [{v.code}]: {v.message} — {v.action}")
        else:
            lines.append("✅ No violations found!")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"EXIT CODE: {'0 (pass)' if report.pass_status else '2 (fail)'}")
        lines.append("=" * 80)
        
        path.write_text('\n'.join(lines), encoding='utf-8')
    
    @staticmethod
    def print_console(report: ValidationReport):
        """Imprime relatório no console (formato problemMatcher)"""
        for v in report.violations:
            location = f"{v.file}:{v.line}:{v.col}" if v.file else "coverage:0:0"
            # Usar ASCII em vez de emojis para compatibilidade Windows console
            print(f"{location}: {v.level} [{v.code}]: {v.message} - {v.action}")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"Summary: {report.summary['error_count']} errors, {report.summary['warning_count']} warnings")
        status_text = "PASS" if report.pass_status else "FAIL"
        print(f"Status: {status_text}")
        print(f"{'='*80}")


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Validate invariants tests against INVARIANTS_TESTING_CANON.md'
    )
    parser.add_argument(
        '--level',
        choices=['basic', 'standard', 'strict'],
        default='strict',
        help='Validation level (default: strict)'
    )
    parser.add_argument(
        '--files-changed',
        nargs='*',
        help='Validate only specific files (pre-commit optimization)'
    )
    parser.add_argument(
        '--inv',
        action='append',
        dest='inv_ids',
        metavar='INV_ID',
        help='Validate only specific invariant(s) by ID (ex: --inv INV-TRAIN-041). Can be specified multiple times.'
    )
    parser.add_argument(
        '--report-json',
        type=Path,
        help='Write JSON report to file'
    )
    parser.add_argument(
        '--report-txt',
        type=Path,
        help='Write TXT report to file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--strict-spec',
        action='store_true',
        help='Strict SPEC mode: SPEC_INVALID/SPEC_MISSING are violations (exit 2), not warnings'
    )
    
    args = parser.parse_args()
    
    try:
        # Determine project root
        script_dir = Path(__file__).parent.resolve()
        project_root = script_dir.parent.parent
        
        # Paths
        invariants_md = project_root / 'docs' / '02_modulos' / 'training' / 'INVARIANTS' / 'INVARIANTS_TRAINING.md'
        tests_dir = project_root / 'Hb Track - Backend' / 'tests' / 'training' / 'invariants'
        
        # Parse invariants
        if args.verbose:
            print(f"Parsing {invariants_md}...")
        parser_obj = InvariantsParser()
        invariants, spec_violations = parser_obj.parse(invariants_md, strict_spec=args.strict_spec)
        
        if args.verbose:
            print(f"Found {len(invariants)} confirmed invariants")
        
        # Find test files
        if args.verbose:
            print(f"Scanning {tests_dir}...")
        classifier = FileClassifier(tests_dir)
        files_by_inv = classifier.find_test_files()
        
        # Derive target_inv_ids from --files-changed or --inv (scope optimization)
        target_inv_ids = None
        
        # Option 1: --inv (direct INV-ID specification)
        if args.inv_ids:
            target_inv_ids = set()
            for inv_id in args.inv_ids:
                # Validate INV-ID exists in specs
                if any(inv.id == inv_id for inv in invariants):
                    target_inv_ids.add(inv_id)
                else:
                    if args.verbose:
                        print(f"Warning: {inv_id} not found in SPEC")
        
        # Option 2: --files-changed (derive INV-IDs from file paths)
        if args.files_changed:
            # Build map: normalized_path(tests.primary) -> inv_id
            inv_by_primary_path = {}
            for inv in invariants:
                if inv.tests and 'primary' in inv.tests:
                    primary_path = inv.tests['primary']
                    # Resolve relative to project_root
                    abs_path = (project_root / primary_path).resolve()
                    # Normalize for Windows case-insensitive comparison
                    normalized_key = str(abs_path).lower()
                    inv_by_primary_path[normalized_key] = inv.id
            
            # Normalize target files
            target_files = []
            for file_arg in args.files_changed:
                # Try relative to project_root
                candidate = project_root / file_arg
                if candidate.exists():
                    target_files.append(str(candidate.resolve()).lower())
                else:
                    # Try as absolute path
                    candidate = Path(file_arg)
                    if candidate.exists():
                        target_files.append(str(candidate.resolve()).lower())
            
            # Match files to inv_ids (union with --inv if both specified)
            files_inv_ids = set()
            for target_file in target_files:
                if target_file in inv_by_primary_path:
                    files_inv_ids.add(inv_by_primary_path[target_file])
            
            # Fallback: extract INV-ID from filename
            if not files_inv_ids:
                for file_arg in args.files_changed:
                    match = re.search(r'test_inv_train_(\d{3})', file_arg)
                    if match:
                        inv_id = f"INV-TRAIN-{match.group(1)}"
                        # Check if exists in specs
                        if any(inv.id == inv_id for inv in invariants):
                            files_inv_ids.add(inv_id)
            
            # Union with --inv scope
            if target_inv_ids is not None:
                target_inv_ids = target_inv_ids.union(files_inv_ids)
            else:
                target_inv_ids = files_inv_ids
        
        # Final scope message
        if args.verbose and target_inv_ids:
            print(f"Scope: validating {len(target_inv_ids)} invariant(s): {sorted(target_inv_ids)}")
        
        # Initialize violations list with SPEC violations from parse
        violations = list(spec_violations)
        
        # Detect UNOWNED_TEST (orphaned test files) in strict-spec mode
        if args.strict_spec:
            owned_inv_ids = {inv.id for inv in invariants}
            unowned_inv_ids = set(files_by_inv.keys()) - owned_inv_ids
            
            # Apply scope if --files-changed
            if target_inv_ids is not None:
                unowned_inv_ids = unowned_inv_ids & target_inv_ids
            
            for unowned_id in sorted(unowned_inv_ids):
                for test_file in files_by_inv[unowned_id]:
                    violations.append(Violation(
                        inv_id=unowned_id,
                        file=str(test_file.path.relative_to(tests_dir.parent.parent.parent)),
                        line=1,
                        col=1,
                        level=args.level,
                        code='UNOWNED_TEST',
                        message=f"Test file for {unowned_id} exists but invariant not found in INVARIANTS_TRAINING.md (orphaned test)",
                        action="Remove file or add invariant to markdown"
                    ))
            
            # Detect SPEC_MISSING (invariants without SPEC blocks) in strict-spec mode
            for inv in invariants:
                # Apply scope if --files-changed
                if target_inv_ids is not None and inv.id not in target_inv_ids:
                    continue
                
                if not inv.is_alias and inv.test_required and not inv.has_spec:
                    violations.append(Violation(
                        inv_id=inv.id,
                        file='docs/02-modulos/training/INVARIANTS_TRAINING.md',
                        line=1,
                        col=1,
                        level=args.level,
                        code='SPEC_MISSING',
                        message=f"{inv.id} requires SPEC block (strict-spec mode enabled)",
                        action="Add SPEC block following documented patterns"
                    ))
        
        # Validate coverage (with scope if --files-changed)
        openapi_path = project_root / 'docs' / '_generated' / 'openapi.json'
        openapi_ids = load_openapi_operation_ids(openapi_path)
        openapi_index = load_openapi_index(openapi_path)
        
        if args.verbose and openapi_ids:
            print(f"Loaded {len(openapi_ids)} operationIds from openapi.json")
        
        validator = RuleValidator(
            level=args.level, 
            verbose=args.verbose, 
            openapi_ids=openapi_ids,
            openapi_index=openapi_index
        )
        if target_inv_ids is not None:
            # Filter invariants and files_by_inv to scope
            scoped_invariants = [inv for inv in invariants if inv.id in target_inv_ids]
            scoped_files_by_inv = {inv_id: files for inv_id, files in files_by_inv.items() if inv_id in target_inv_ids}
            violations.extend(validator.validate_coverage(scoped_invariants, scoped_files_by_inv))
        else:
            violations.extend(validator.validate_coverage(invariants, files_by_inv))
        
        # Analyze each principal file
        for inv in invariants:
            # Skip aliases
            if inv.is_alias or not inv.test_required:
                continue
            
            # Apply scope if --files-changed (use target_inv_ids, not files_to_analyze)
            if target_inv_ids is not None and inv.id not in target_inv_ids:
                continue
            
            files = files_by_inv.get(inv.id, [])
            principal_files = [f for f in files if f.is_principal]
            
            if len(principal_files) == 1:
                file_path = principal_files[0].path
                
                if args.verbose:
                    print(f"Analyzing {file_path.name}...")
                
                # AST analysis
                analyzer = ASTAnalyzer(file_path)
                analysis = analyzer.analyze()

                # DoD-0
                violations.extend(validator.validate_dod0(analysis, file_path))
                
                # Obligations (strict only)
                violations.extend(validator.validate_obligations(analysis, file_path, inv, verbose=args.verbose))
                
                # Class-specific rules
                # Determinar classes a validar (SPEC ou legacy)
                classes_to_validate = inv.primary_classes
                
                for class_type in classes_to_validate:
                    # Check 1: Class must be in the allowed taxonomy
                    if class_type not in ALLOWED_CLASSES:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=1,
                            col=0,
                            level='ERROR',
                            code='CLASS_UNKNOWN',
                            message=f"Unknown invariant class: {class_type}. Not in allowed taxonomy.",
                            action=f"Change class to one of the allowed classes ({', '.join(sorted(ALLOWED_CLASSES))}) or add {class_type} to ALLOWED_CLASSES in verify_invariants_tests.py"
                        ))
                        continue  # Skip further validation for this class
                    
                    # Check 2: Class must have an implemented validator
                    if class_type not in IMPLEMENTED_CLASSES:
                        violations.append(Violation(
                            inv_id=analysis.inv_id,
                            file=str(file_path),
                            line=1,
                            col=0,
                            level='ERROR',
                            code='CLASS_NOT_IMPLEMENTED',
                            message=f"Class {class_type} is in taxonomy but validator not yet implemented.",
                            action=f"Implement validator for class {class_type} in verify_invariants_tests.py or mark unit as required: false in SPEC until validator is ready"
                        ))
                        continue  # Skip further validation for this class
                    
                    # Dispatch to appropriate validator
                    if class_type == 'A':
                        violations.extend(validator.validate_class_a(analysis, file_path))
                    elif class_type == 'B':
                        violations.extend(validator.validate_class_b(analysis, file_path, inv))
                    elif class_type == 'C1':
                        violations.extend(validator.validate_class_c1(analysis, file_path, inv))
                    elif class_type == 'C2':
                        violations.extend(validator.validate_class_c2(analysis, file_path, inv))
                    elif class_type == 'D':
                        violations.extend(validator.validate_class_d(analysis, file_path, inv))
                    elif class_type == 'E1':
                        violations.extend(validator.validate_class_e1(analysis, file_path, inv))
                    elif class_type == 'F':
                        violations.extend(validator.validate_class_f(analysis, file_path, inv))
                    elif class_type == 'C':
                        # Legacy 'C' class support (maps to C1/C2 conceptually)
                        # For now, no specific validator, just skip
                        pass
                    # Adicionar outras classes conforme necessário
                
                # Anti-patterns (all files)
                violations.extend(validator.validate_anti_patterns(analysis, file_path))
        
        # Generate report
        covered = len([inv for inv in invariants if inv.id in files_by_inv and any(f.is_principal for f in files_by_inv[inv.id])])
        report = ReportGenerator.generate(violations, args.level, len(invariants), covered)
        
        # Write reports
        if args.report_json:
            ReportGenerator.write_json(report, args.report_json)
            if args.verbose:
                print(f"JSON report written to {args.report_json}")
        
        if args.report_txt:
            ReportGenerator.write_txt(report, args.report_txt)
            if args.verbose:
                print(f"TXT report written to {args.report_txt}")
        
        # Print to console
        ReportGenerator.print_console(report)
        
        # Exit code
        sys.exit(0 if report.pass_status else 2)
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
