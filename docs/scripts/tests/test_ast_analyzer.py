from __future__ import annotations
import ast
from pathlib import Path

def _repo_root() -> Path:
    p = Path(__file__).resolve()
    # docs/scripts/tests/test_ast_analyzer.py -> repo root is 4 levels up
    return p.parents[3] # docs/scripts/tests/test.py -> docs/scripts/tests (0), docs/scripts (1), docs (2), root (3)

def _verify_script_path() -> Path:
    path = _repo_root() / "docs" / "scripts" / "verify_invariants_tests.py"
    if not path.exists():
        # Debug path if it fails
        print(f"DEBUG: Repo root evaluated as: {_repo_root()}")
        print(f"DEBUG: Checking path: {path}")
    assert path.exists(), f"verify script not found: {path}"
    return path

def _load_source() -> str:
    return _verify_script_path().read_text(encoding="utf-8")

def _parse_tree() -> ast.AST:
    return ast.parse(_load_source())

def _find_class(tree: ast.AST, class_name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"class {class_name} not found")

def _find_method(cls: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"method {cls.name}.{name} not found")

def _calls_name(fn: ast.AST, target: str) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            callee = node.func
            # self._handle_function_common(...)
            if isinstance(callee, ast.Attribute) and callee.attr == target:
                return True
            # _handle_function_common(...)
            if isinstance(callee, ast.Name) and callee.id == target:
                return True
    return False

def test_visitors_delegate_to_handle_function_common():
    tree = _parse_tree()
    cls = _find_class(tree, "ASTAnalyzer")
    visit_fn = _find_method(cls, "visit_FunctionDef")
    visit_async = _find_method(cls, "visit_AsyncFunctionDef")

    assert _calls_name(visit_fn, "_handle_function_common"), "visit_FunctionDef must call _handle_function_common"
    assert _calls_name(visit_async, "_handle_function_common"), "visit_AsyncFunctionDef must call _handle_function_common"

def test_handle_function_node_supports_posonly_and_kwonly_args():
    src = _load_source()
    # Robust textual lock: prevents accidental removal during refactors.
    assert "posonlyargs" in src, "posonlyargs must be handled in _handle_function_node"
    assert "kwonlyargs" in src, "kwonlyargs must be handled in _handle_function_node"

def test_has_pytest_raises_supports_asyncwith():
    src = _load_source()
    # Lock: require AsyncWith reference for async context manager patterns.
    assert "AsyncWith" in src, "_has_pytest_raises must consider ast.AsyncWith"
