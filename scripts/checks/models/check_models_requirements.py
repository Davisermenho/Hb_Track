#!/usr/bin/env python3
# HB_SCRIPT_KIND: CHECK
# HB_SCRIPT_SIDE_EFFECTS: DB_READ, FS_READ
# HB_SCRIPT_SCOPE: models
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: python scripts/checks/models/check_models_requirements.py
# HB_SCRIPT_OUTPUTS: exit_code, violations_list

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

EXIT_REQUIREMENTS_VIOLATION = 4


@dataclass(frozen=True)
class ForeignKeySpec:
    name: str
    reference: str
    local_columns: tuple[str, ...] = ()
    ondelete: str | None = None
    onupdate: str | None = None
    use_alter: bool | None = None
    line_no: int | None = None


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    nullable: bool
    nullable_explicit: bool
    is_primary_key: bool
    type_key: str | None
    default_kind: str | None = None
    default_value: str | None = None
    line_no: int | None = None


@dataclass(frozen=True)
class CheckSpec:
    name: str
    line_no: int | None = None


@dataclass(frozen=True)
class UniqueConstraintSpec:
    name: str
    line_no: int | None = None


@dataclass(frozen=True)
class IndexSpec:
    name: str
    unique: bool
    where: str | None
    line_no: int | None = None


CYCLE_FK_NAMES: set[str] = {
    "fk_teams_season_id",
    "fk_seasons_team_id",
}

ACCEPTABLE_EQUIVALENCES: set[tuple[str, str]] = {
    ("varchar|None", "text"),
    ("text", "varchar|None"),
}

REJECTED_EQUIVALENCES: set[tuple[str, str]] = {
    ("text", "varchar|255"),
    ("varchar|255", "text"),
    ("varchar|50", "varchar|64"),
    ("varchar|64", "varchar|50"),
}

DEFAULT_EXCEPTIONS_FILE = Path(".hb_guard") / "model_requirements_exceptions.json"


class _SpecsMap(dict):
    """Compatibility map for parser helpers.

    - Keeps mapping behavior used by internal validators/tests.
    - Supports slice access (e.g. items[:5]) returning value list slices.
    - Iterates over values to support external sampling scripts.
    """

    def __getitem__(self, key):
        if isinstance(key, slice):
            return list(self.values())[key]
        return super().__getitem__(key)

    def __iter__(self):
        return iter(self.values())


def _normalize_ident(value: str) -> str:
    return value.strip().strip('"').lower()


def _normalize_reference(value: str) -> str:
    value = value.strip().strip('"')
    parts = [p.strip().strip('"') for p in value.split(".") if p.strip()]
    if len(parts) == 2:
        return f"{parts[0].lower()}.{parts[1].lower()}"
    return value.lower()


def _extract_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _is_foreign_key_call(node: ast.Call) -> bool:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id == "ForeignKey"
    if isinstance(fn, ast.Attribute):
        return fn.attr == "ForeignKey"
    return False


def _extract_fk_call(node: ast.Call) -> ForeignKeySpec | None:
    if not _is_foreign_key_call(node):
        return None
    if not node.args:
        return None

    reference_raw = _extract_str(node.args[0])
    if not reference_raw:
        return None

    name: str | None = None
    ondelete: str | None = None
    use_alter: bool | None = None

    for kw in node.keywords:
        if kw.arg == "name":
            name = _extract_str(kw.value)
        elif kw.arg == "ondelete":
            ondelete = _extract_str(kw.value)
        elif kw.arg == "use_alter":
            use_alter = _extract_bool(kw.value)

    if not name:
        return None

    return ForeignKeySpec(
        name=_normalize_ident(name),
        reference=_normalize_reference(reference_raw),
        local_columns=(),
        ondelete=ondelete.upper() if ondelete else None,
        onupdate=None,
        use_alter=use_alter,
        line_no=getattr(node, "lineno", None),
    )


def _is_column_call(node: ast.Call) -> bool:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id in {"mapped_column", "Column"}
    if isinstance(fn, ast.Attribute):
        return fn.attr in {"mapped_column", "Column"}
    return False


def _extract_kw_bool(call: ast.Call, key: str) -> bool | None:
    for kw in call.keywords:
        if kw.arg == key:
            return _extract_bool(kw.value)
    return None


def _extract_kw_int(call: ast.Call, key: str) -> int | None:
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
            return kw.value.value
    return None


def _extract_kw_node(call: ast.Call, key: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == key:
            return kw.value
    return None


def _type_key(kind: str, *parts: object) -> str:
    tail = "|".join("" if p is None else str(p) for p in parts)
    return f"{kind}|{tail}" if parts else kind


def _schema_type_to_key(type_expr: str) -> str | None:
    t = re.sub(r"\s+", " ", type_expr.strip().lower())

    if t in {"uuid"}:
        return _type_key("uuid")
    if t in {"integer", "int4", "int"}:
        return _type_key("integer")
    if t in {"bigint", "int8"}:
        return _type_key("bigint")
    if t in {"smallint", "int2"}:
        return _type_key("smallint")
    if t == "boolean":
        return _type_key("boolean")
    if t == "date":
        return _type_key("date")
    if t == "timestamp with time zone":
        return _type_key("datetime", "tz")
    if t == "timestamp without time zone":
        return _type_key("datetime", "no_tz")
    if t == "text":
        return _type_key("text")
    if t.startswith("character varying"):
        m = re.match(r"character varying\s*\((\d+)\)", t)
        if m:
            return _type_key("varchar", int(m.group(1)))
        return _type_key("varchar", None)
    if t.startswith("numeric"):
        m = re.match(r"numeric\s*\((\d+)\s*,\s*(\d+)\)", t)
        if m:
            return _type_key("numeric", int(m.group(1)), int(m.group(2)))
        return _type_key("numeric", None, None)

    return None


def _extract_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _model_type_to_key(type_node: ast.AST | None) -> str | None:
    if type_node is None:
        return None

    if isinstance(type_node, ast.Call):
        name = _extract_call_name(type_node.func)
        if not name:
            return None
        name_l = name.lower()

        if name_l in {"uuid", "pg_uuid"}:
            return _type_key("uuid")
        if name_l == "integer":
            return _type_key("integer")
        if name_l == "biginteger":
            return _type_key("bigint")
        if name_l == "smallinteger":
            return _type_key("smallint")
        if name_l == "boolean":
            return _type_key("boolean")
        if name_l == "date":
            return _type_key("date")
        if name_l == "datetime":
            tz = _extract_kw_bool(type_node, "timezone")
            if tz is True:
                return _type_key("datetime", "tz")
            # policy: DateTime() sem timezone explícito é aceito para no_tz
            return _type_key("datetime", "no_tz")
        if name_l == "text":
            return _type_key("text")
        if name_l == "string":
            # String(N) or String(length=N) or String()
            if type_node.args and isinstance(type_node.args[0], ast.Constant) and isinstance(type_node.args[0].value, int):
                return _type_key("varchar", int(type_node.args[0].value))
            length_kw = _extract_kw_int(type_node, "length")
            if length_kw is not None:
                return _type_key("varchar", length_kw)
            return _type_key("varchar", None)
        if name_l == "numeric":
            precision = None
            scale = None
            if len(type_node.args) >= 1 and isinstance(type_node.args[0], ast.Constant) and isinstance(type_node.args[0].value, int):
                precision = int(type_node.args[0].value)
            if len(type_node.args) >= 2 and isinstance(type_node.args[1], ast.Constant) and isinstance(type_node.args[1].value, int):
                scale = int(type_node.args[1].value)
            if precision is None:
                precision = _extract_kw_int(type_node, "precision")
            if scale is None:
                scale = _extract_kw_int(type_node, "scale")
            return _type_key("numeric", precision, scale)

    if isinstance(type_node, ast.Name):
        n = type_node.id.lower()
        if n in {"uuid", "pg_uuid"}:
            return _type_key("uuid")
        if n == "integer":
            return _type_key("integer")
        if n == "biginteger":
            return _type_key("bigint")
        if n == "smallinteger":
            return _type_key("smallint")
        if n == "boolean":
            return _type_key("boolean")
        if n == "date":
            return _type_key("date")
        if n == "datetime":
            return _type_key("datetime", "no_tz")
        if n == "text":
            return _type_key("text")
        if n == "string":
            return _type_key("varchar", None)
        if n == "numeric":
            return _type_key("numeric", None, None)

    return None


def _extract_column_type_arg(call: ast.Call) -> ast.AST | None:
    if not call.args:
        return None

    first = call.args[0]
    # mapped_column may have ForeignKey as first positional argument.
    if isinstance(first, ast.Call) and _is_foreign_key_call(first):
        return None
    return first


def _extract_schema_type_expr(rest: str) -> str:
    # stop before DEFAULT/NOT NULL/NULL/CONSTRAINT/etc
    m = re.match(
        r"^(?P<typ>.+?)(?=\s+DEFAULT\b|\s+NOT\s+NULL\b|\s+NULL\b|\s+CONSTRAINT\b|\s+PRIMARY\s+KEY\b|\s+REFERENCES\b|$)",
        rest,
        flags=re.IGNORECASE,
    )
    return (m.group("typ") if m else rest).strip()


def _extract_default_expr(rest: str) -> str | None:
    m = re.search(
        r"\bDEFAULT\s+(?P<default>.+?)(?=\s+NOT\s+NULL\b|\s+NULL\b|\s+CONSTRAINT\b|\s+PRIMARY\s+KEY\b|\s+REFERENCES\b|$)",
        rest,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    return m.group("default").strip()


def _classify_default(default_expr: str | None) -> tuple[str | None, str | None]:
    if default_expr is None:
        return None, None

    raw = default_expr.strip()
    lower = raw.lower()

    # deterministic literals first
    if lower in {"0", "1", "true", "false", "null"}:
        return "default_literal", lower
    if raw.startswith("'"):
        return "default_literal", raw

    # everything function-like stays non-blocking classification
    if "(" in raw and ")" in raw:
        return "default_function", raw

    return "default_literal", raw


def _extract_default_from_ast(node: ast.AST | None) -> tuple[str | None, str | None]:
    if node is None:
        return None, None

    if isinstance(node, ast.Constant):
        if node.value is None:
            return "default_literal", "null"
        if isinstance(node.value, bool):
            return "default_literal", "true" if node.value else "false"
        if isinstance(node.value, (int, float)):
            return "default_literal", str(node.value)
        if isinstance(node.value, str):
            return "default_literal", repr(node.value)

    if isinstance(node, ast.Call):
        fn_name = _extract_call_name(node.func)
        if fn_name == "text" and node.args:
            txt = _extract_str(node.args[0])
            if txt is not None:
                kind, value = _classify_default(txt.strip())
                if kind is not None:
                    return kind, value
                return "default_function", txt.strip()
        # default=uuid4 style and similar function defaults
        if fn_name:
            return "default_function", fn_name

    if isinstance(node, ast.Name):
        return "default_function", node.id

    if isinstance(node, ast.Attribute):
        return "default_function", node.attr

    return None, None


def _norm_default_value(v: str | None) -> str | None:
    if v is None:
        return None
    vv = v.strip().strip("'").strip('"').lower()
    vv = re.sub(r"\s+", " ", vv)
    vv = vv.replace("public.", "")
    # normalize explicit casts in pg_dump output, keep semantic core
    vv = re.sub(r"::[a-z_ ]+", "", vv)
    return vv


def _get_create_table_body(schema_text: str, table: str) -> str:
    table_pattern = re.compile(
        rf"CREATE\s+TABLE\s+public\.{re.escape(table)}\s*\((?P<body>.*?)\);",
        flags=re.IGNORECASE | re.DOTALL,
    )
    m = table_pattern.search(schema_text)
    if not m:
        raise RuntimeError(f"CREATE TABLE for {table!r} not found in schema.sql")
    return m.group("body")


def _fk_ondelete_equivalent(expected: str | None, got: str | None) -> bool:
    norm_expected = re.sub(r"\s+", " ", (expected or "").strip().upper()) or None
    norm_got = re.sub(r"\s+", " ", (got or "").strip().upper()) or None

    # Schema may omit ON DELETE (Postgres defaults to NO ACTION).
    # Accept explicit model RESTRICT/NO ACTION in that case.
    if norm_expected is None:
        return norm_got in {None, "RESTRICT", "NO ACTION"}

    if norm_expected in {"RESTRICT", "NO ACTION"} and norm_got in {"RESTRICT", "NO ACTION"}:
        return True

    return norm_expected == norm_got


def _line_suffix(line_no: int | None) -> str:
    return f" line={line_no}" if line_no is not None else ""


def _types_equivalent(expected: str, got: str) -> bool:
    if expected == got:
        return True

    pair = (expected, got)
    if pair in REJECTED_EQUIVALENCES:
        return False
    if pair in ACCEPTABLE_EQUIVALENCES:
        return True
    return False


def _load_lenient_exceptions(root: Path) -> list[dict]:
    p = root / DEFAULT_EXCEPTIONS_FILE
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        items = data.get("exceptions", [])
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def _violation_code(v: str) -> str:
    return v.split(":", 1)[0].strip()


def _apply_lenient_exceptions(
    violations: list[str],
    table: str,
    model_path: Path,
    exceptions: list[dict],
) -> tuple[list[str], list[tuple[str, dict]]]:
    remaining: list[str] = []
    applied: list[tuple[str, dict]] = []
    model_path_norm = str(model_path).replace("\\", "/").lower()

    for v in violations:
        code = _violation_code(v)
        matched_exc: dict | None = None
        for exc in exceptions:
            exc_table = str(exc.get("table", "")).strip().lower()
            if exc_table and exc_table != table.lower():
                continue

            exc_model_path = str(exc.get("model_path", "")).strip().replace("\\", "/").lower()
            if exc_model_path and exc_model_path not in model_path_norm:
                continue

            ignore = exc.get("ignore", [])
            if not isinstance(ignore, list):
                continue
            ignore_codes = {str(x).strip() for x in ignore}
            if code not in ignore_codes:
                continue

            matched_exc = exc
            break

        if matched_exc:
            applied.append((v, matched_exc))
        else:
            remaining.append(v)

    return remaining, applied


def _parse_model_fks(model_path: Path, table: str) -> dict[str, set[ForeignKeySpec]]:
    """Parse FKs from the specific class matching __tablename__=table.
    
    NOTE: This function now filters by class to avoid false positives
    when multiple classes exist in the same file (e.g., person.py with
    Person, PersonAddress, PersonContact, PersonDocument, PersonMedia).
    """
    tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
    try:
        target_class = _find_model_class_node(tree, table, model_path)
    except RuntimeError:
        # Class not found - return empty (will cause MISSING_FK violations)
        return {}
    
    by_name: dict[str, set[ForeignKeySpec]] = {}

    # Only walk the target class, not the entire file
    for node in ast.walk(target_class):
        if not isinstance(node, ast.Call):
            continue
        fk = _extract_fk_call(node)
        if not fk:
            continue
        by_name.setdefault(fk.name, set()).add(fk)

    return by_name


def _find_model_class_node(tree: ast.Module, table: str, model_path: Path) -> ast.ClassDef:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        class_table: str | None = None
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        class_table = _extract_str(stmt.value)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "__tablename__":
                class_table = _extract_str(stmt.value)

        if class_table == table:
            return node

    raise RuntimeError(f"class with __tablename__={table!r} not found in {model_path}")


def _parse_model_constraints(model_path: Path, table: str) -> dict[str, _SpecsMap]:
    tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
    target_class = _find_model_class_node(tree, table, model_path)

    checks: dict[str, CheckSpec] = {}
    uniques: dict[str, UniqueConstraintSpec] = {}
    indexes: dict[str, IndexSpec] = {}
    fks: dict[str, ForeignKeySpec] = {}

    def _capture_constraint_call(call: ast.Call) -> None:
        fn_name = _extract_call_name(call.func)
        if not fn_name:
            return

        if fn_name == "CheckConstraint":
            name = None
            for kw in call.keywords:
                if kw.arg == "name":
                    name = _extract_str(kw.value)
                    break
            if name:
                checks[_normalize_ident(name)] = CheckSpec(
                    name=_normalize_ident(name),
                    line_no=getattr(call, "lineno", None),
                )
            return

        if fn_name == "UniqueConstraint":
            name = None
            for kw in call.keywords:
                if kw.arg == "name":
                    name = _extract_str(kw.value)
                    break
            if name:
                uniques[_normalize_ident(name)] = UniqueConstraintSpec(
                    name=_normalize_ident(name),
                    line_no=getattr(call, "lineno", None),
                )
            return

        if fn_name == "Index":
            idx_name = _extract_str(call.args[0]) if call.args else None
            if not idx_name:
                return
            unique = _extract_kw_bool(call, "unique") is True

            where: str | None = None
            where_node = _extract_kw_node(call, "postgresql_where")
            if isinstance(where_node, ast.Call):
                where_fn = _extract_call_name(where_node.func)
                if where_fn == "text" and where_node.args:
                    where = _extract_str(where_node.args[0])

            indexes[_normalize_ident(idx_name)] = IndexSpec(
                name=_normalize_ident(idx_name),
                unique=unique,
                where=re.sub(r"\s+", " ", where.strip()) if where else None,
                line_no=getattr(call, "lineno", None),
            )

    # __table_args__ static tuple/list constraints
    for stmt in target_class.body:
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "__table_args__":
                    value = stmt.value
                    break
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "__table_args__":
            value = stmt.value

        if value is None:
            continue

        if isinstance(value, (ast.Tuple, ast.List)):
            for el in value.elts:
                if isinstance(el, ast.Call):
                    _capture_constraint_call(el)
        elif isinstance(value, ast.Call):
            _capture_constraint_call(value)

    # Inline ForeignKey(...) inside Column()/mapped_column()
    for stmt in target_class.body:
        col_name: str | None = None
        col_call: ast.Call | None = None
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
            col_name = stmt.target.id
            col_call = stmt.value
        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Call):
            col_name = stmt.targets[0].id
            col_call = stmt.value

        if not col_name or not col_call or not _is_column_call(col_call):
            continue

        for arg in col_call.args:
            if isinstance(arg, ast.Call):
                fk = _extract_fk_call(arg)
                if fk and fk.name:
                    fks[fk.name] = ForeignKeySpec(
                        name=fk.name,
                        reference=fk.reference,
                        local_columns=(col_name,),
                        ondelete=fk.ondelete,
                        onupdate=fk.onupdate,
                        use_alter=fk.use_alter,
                        line_no=fk.line_no,
                    )

    return {
        "checks": _SpecsMap(checks),
        "uniques": _SpecsMap(uniques),
        "indexes": _SpecsMap(indexes),
        "fks": _SpecsMap(fks),
    }


def _parse_model_columns(model_path: Path, table: str) -> dict[str, ColumnSpec]:
    tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
    target_class = _find_model_class_node(tree, table, model_path)

    columns: dict[str, ColumnSpec] = {}

    def _capture_col(col_name: str, call: ast.Call) -> None:
        if not col_name:
            return
        primary_key = _extract_kw_bool(call, "primary_key") is True
        nullable_kw = _extract_kw_bool(call, "nullable")
        nullable_explicit = nullable_kw is not None
        type_node = _extract_column_type_arg(call)
        type_key = _model_type_to_key(type_node)

        server_default_node = _extract_kw_node(call, "server_default")
        default_kind, default_value = _extract_default_from_ast(server_default_node)

        # Policy: nullable must be explicit (except PK); if missing, keep as non-null marker for later violation.
        nullable = bool(nullable_kw) if nullable_kw is not None else False
        columns[col_name] = ColumnSpec(
            name=col_name,
            nullable=nullable,
            nullable_explicit=nullable_explicit,
            is_primary_key=primary_key,
            type_key=type_key,
            default_kind=default_kind,
            default_value=default_value,
            line_no=getattr(call, "lineno", None),
        )

    for stmt in target_class.body:
        # typed assignment: foo: Mapped[...] = mapped_column(...)
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
            if _is_column_call(stmt.value):
                _capture_col(stmt.target.id, stmt.value)
            continue

        # plain assignment: foo = Column(...)
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Call):
            if _is_column_call(stmt.value):
                _capture_col(stmt.targets[0].id, stmt.value)

    return columns


def _parse_schema_columns(schema_text: str, table: str) -> dict[str, ColumnSpec]:
    body = _get_create_table_body(schema_text, table)
    lines = [ln.strip().rstrip(",") for ln in body.splitlines() if ln.strip()]

    columns: dict[str, ColumnSpec] = {}
    pk_columns: set[str] = set()

    # collect PK columns from table constraints
    for ln in lines:
        up = ln.upper()
        if "PRIMARY KEY" in up:
            pk_m = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", ln, flags=re.IGNORECASE)
            if pk_m:
                pk_cols = [c.strip().strip('"') for c in pk_m.group(1).split(",")]
                pk_columns.update(_normalize_ident(c) for c in pk_cols if c)

    # collect PK columns from ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY (...) statements
    alter_pk_re = re.compile(
        rf"ALTER\s+TABLE\s+ONLY\s+public\.{re.escape(table)}\s+"
        r"ADD\s+CONSTRAINT\s+[\w\"]+\s+PRIMARY\s+KEY\s*\((?P<cols>[^)]+)\)",
        flags=re.IGNORECASE,
    )
    for m in alter_pk_re.finditer(schema_text):
        pk_cols = [c.strip().strip('"') for c in m.group("cols").split(",")]
        pk_columns.update(_normalize_ident(c) for c in pk_cols if c)

    for ln in lines:
        up = ln.upper()
        if up.startswith("CONSTRAINT ") or up.startswith("PRIMARY KEY") or up.startswith("UNIQUE ") or up.startswith("CHECK ") or up.startswith("FOREIGN KEY"):
            continue

        col_m = re.match(r'^"?(?P<name>[A-Za-z_][\w]*)"?\s+(?P<rest>.+)$', ln)
        if not col_m:
            continue

        name = _normalize_ident(col_m.group("name"))
        rest = col_m.group("rest")
        schema_type_expr = _extract_schema_type_expr(rest)
        type_key = _schema_type_to_key(schema_type_expr)
        default_expr = _extract_default_expr(rest)
        default_kind, default_value = _classify_default(default_expr)
        not_null = bool(re.search(r"\bNOT\s+NULL\b", rest, flags=re.IGNORECASE))
        inline_pk = bool(re.search(r"\bPRIMARY\s+KEY\b", rest, flags=re.IGNORECASE))
        is_pk = inline_pk or (name in pk_columns)

        columns[name] = ColumnSpec(
            name=name,
            nullable=not not_null,
            nullable_explicit=True,
            is_primary_key=is_pk,
            type_key=type_key,
            default_kind=default_kind,
            default_value=default_value,
        )

    return _SpecsMap(columns)


def _parse_schema_fks(schema_text: str, table: str) -> dict[str, ForeignKeySpec]:
    pattern = re.compile(
        r"ALTER\s+TABLE\s+ONLY\s+public\.(?P<table>[\w\"]+)\s+"
        r"ADD\s+CONSTRAINT\s+(?P<name>[\w\"]+)\s+"
        r"FOREIGN\s+KEY\s*\((?P<local_cols>[^)]*)\)\s+"
        r"REFERENCES\s+public\.(?P<ref_table>[\w\"]+)\s*\((?P<ref_col>[\w\"\s,]+)\)"
        r"(?P<tail>[^;]*);",
        flags=re.IGNORECASE | re.DOTALL,
    )

    expected: dict[str, ForeignKeySpec] = {}
    table_norm = _normalize_ident(table)

    for m in pattern.finditer(schema_text):
        ddl_table = _normalize_ident(m.group("table"))
        if ddl_table != table_norm:
            continue

        name = _normalize_ident(m.group("name"))
        local_cols = tuple(
            _normalize_ident(c)
            for c in m.group("local_cols").split(",")
            if c.strip()
        )
        ref_table = _normalize_ident(m.group("ref_table"))
        ref_col = _normalize_ident(m.group("ref_col").split(",")[0])

        tail = m.group("tail") or ""
        ondelete_match = re.search(
            r"ON\s+DELETE\s+([A-Z\s]+?)(?:\s+ON\s+UPDATE|\s+DEFERRABLE|\s+NOT\s+DEFERRABLE|$)",
            tail,
            flags=re.IGNORECASE,
        )
        if ondelete_match:
            ondelete = re.sub(r"\s+", " ", ondelete_match.group(1).strip().upper())
        else:
            ondelete = None

        onupdate_match = re.search(
            r"ON\s+UPDATE\s+([A-Z\s]+?)(?:\s+ON\s+DELETE|\s+DEFERRABLE|\s+NOT\s+DEFERRABLE|$)",
            tail,
            flags=re.IGNORECASE,
        )
        if onupdate_match:
            onupdate = re.sub(r"\s+", " ", onupdate_match.group(1).strip().upper())
        else:
            onupdate = None

        expected[name] = ForeignKeySpec(
            name=name,
            reference=f"{ref_table}.{ref_col}",
            local_columns=local_cols,
            ondelete=ondelete,
            onupdate=onupdate,
            use_alter=None,
        )

    return _SpecsMap(expected)


def _parse_columns(schema_text: str, table: str) -> dict[str, ColumnSpec]:
    return _parse_schema_columns(schema_text, table)


def _parse_fks(schema_text: str, table: str) -> dict[str, ForeignKeySpec]:
    return _parse_schema_fks(schema_text, table)


def _parse_checks(schema_text: str, table: str) -> dict[str, CheckSpec]:
    items: dict[str, CheckSpec] = {}
    body = _get_create_table_body(schema_text, table)
    for m in re.finditer(r"CONSTRAINT\s+(?P<name>[\w\"]+)\s+CHECK\b", body, flags=re.IGNORECASE):
        name = _normalize_ident(m.group("name"))
        items[name] = CheckSpec(name=name)

    alter_re = re.compile(
        rf"ALTER\s+TABLE\s+ONLY\s+public\.{re.escape(table)}\s+ADD\s+CONSTRAINT\s+(?P<name>[\w\"]+)\s+CHECK\b",
        flags=re.IGNORECASE,
    )
    for m in alter_re.finditer(schema_text):
        name = _normalize_ident(m.group("name"))
        items[name] = CheckSpec(name=name)
    return _SpecsMap(items)


def _parse_unique_constraints(schema_text: str, table: str) -> dict[str, UniqueConstraintSpec]:
    items: dict[str, UniqueConstraintSpec] = {}
    body = _get_create_table_body(schema_text, table)
    for m in re.finditer(r"CONSTRAINT\s+(?P<name>[\w\"]+)\s+UNIQUE\b", body, flags=re.IGNORECASE):
        name = _normalize_ident(m.group("name"))
        items[name] = UniqueConstraintSpec(name=name)

    alter_re = re.compile(
        rf"ALTER\s+TABLE\s+ONLY\s+public\.{re.escape(table)}\s+ADD\s+CONSTRAINT\s+(?P<name>[\w\"]+)\s+UNIQUE\b",
        flags=re.IGNORECASE,
    )
    for m in alter_re.finditer(schema_text):
        name = _normalize_ident(m.group("name"))
        items[name] = UniqueConstraintSpec(name=name)
    return _SpecsMap(items)


def _parse_indexes(schema_text: str, table: str) -> dict[str, IndexSpec]:
    items: dict[str, IndexSpec] = {}
    pattern = re.compile(
        rf"CREATE\s+(?P<uniq>UNIQUE\s+)?INDEX\s+(?P<name>[\w\"]+)\s+ON\s+public\.{re.escape(table)}\b(?P<tail>[^;]*);",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(schema_text):
        name = _normalize_ident(m.group("name"))
        tail = m.group("tail") or ""
        where_m = re.search(r"\bWHERE\s+(?P<where>.+)$", tail, flags=re.IGNORECASE | re.DOTALL)
        where = re.sub(r"\s+", " ", where_m.group("where").strip()) if where_m else None
        items[name] = IndexSpec(
            name=name,
            unique=bool(m.group("uniq")),
            where=where,
        )
    return _SpecsMap(items)


def _find_model_path(root: Path, table: str) -> Path:
    table_re = re.compile(rf"__tablename__\s*=\s*['\"]{re.escape(table)}['\"]")
    
    # Try root / "app" / "models" first (for direct backend execution)
    models_dir = root / "app" / "models"
    if not models_dir.exists():
        # Try "Hb Track - Backend" subdirectory (for repo root execution)
        models_dir = root / "Hb Track - Backend" / "app" / "models"
    
    for path in sorted(models_dir.glob("*.py")):
        txt = path.read_text(encoding="utf-8", errors="replace")
        if table_re.search(txt):
            return path
    
    raise FileNotFoundError(f"model file not found for table={table} (searched: {models_dir})")


def _validate_fk_profile(root: Path, table: str) -> int:
    violations, model_path, fk_count = _collect_fk_violations(root, table)

    if violations:
        print(f"[FAIL] model_requirements fk profile violations (table={table})")
        print(f"[INFO] model_path={model_path}")
        for v in violations:
            print(f"  - {v}")
        return EXIT_REQUIREMENTS_VIOLATION

    print(f"[OK] model_requirements fk profile passed (table={table})")
    print(f"[INFO] model_path={model_path}")
    print(f"[INFO] fk_count={fk_count}")
    return 0


def _collect_fk_violations(root: Path, table: str) -> tuple[list[str], Path, int]:
    schema_path = root / "docs" / "_generated" / "schema.sql"
    if not schema_path.exists():
        return [f"SCHEMA_NOT_FOUND: {schema_path}"], root / "app" / "models", 0

    model_path = _find_model_path(root, table)
    schema_text = schema_path.read_text(encoding="utf-8", errors="replace")

    expected = _parse_schema_fks(schema_text, table)
    found_by_name = _parse_model_fks(model_path, table)
    violations: list[str] = []

    for name, exp in sorted(expected.items()):
        candidates = found_by_name.get(name)
        if not candidates:
            violations.append(f"MISSING_FK: {name} model_line=None")
            continue

        matched = any(
            c.reference == exp.reference and _fk_ondelete_equivalent(exp.ondelete, c.ondelete)
            for c in candidates
        )
        if not matched:
            got = ", ".join(
                f"ref={c.reference} ondelete={c.ondelete} line={c.line_no}" for c in sorted(candidates, key=lambda x: (x.reference, str(x.ondelete)))
            )
            violations.append(
                f"FK_MISMATCH: {name} expected(ref={exp.reference}, ondelete={exp.ondelete}) got({got})"
            )

        if name in CYCLE_FK_NAMES:
            missing_use_alter = [c for c in candidates if c.use_alter is not True]
            if missing_use_alter:
                got_lines = ",".join(str(c.line_no) for c in missing_use_alter)
                violations.append(
                    f"CYCLE_USE_ALTER_MISSING: {name} expected_use_alter=True model_line={got_lines}"
                )

    for name in sorted(found_by_name.keys()):
        if name not in expected:
            sample = sorted(found_by_name[name], key=lambda x: (x.reference, str(x.ondelete)))[0]
            violations.append(f"EXTRA_FK: {name} model_line={sample.line_no}")

    return violations, model_path, len(expected)


def _validate_columns_nullable_profile(root: Path, table: str) -> tuple[list[str], Path, dict[str, ColumnSpec], dict[str, ColumnSpec]]:
    schema_path = root / "docs" / "_generated" / "schema.sql"
    model_path = _find_model_path(root, table)
    schema_text = schema_path.read_text(encoding="utf-8", errors="replace")

    expected_cols = _parse_schema_columns(schema_text, table)
    model_cols = _parse_model_columns(model_path, table)

    violations: list[str] = []

    expected_names = set(expected_cols.keys())
    model_names = set(model_cols.keys())

    for col in sorted(expected_names - model_names):
        violations.append(f"MISSING_COLUMN: {col} model_line=None")
    for col in sorted(model_names - expected_names):
        got = model_cols[col]
        violations.append(f"EXTRA_COLUMN: {col} model_line={got.line_no}")

    for col in sorted(expected_names & model_names):
        exp = expected_cols[col]
        got = model_cols[col]
        # Ignore nullability check on PKs
        if exp.is_primary_key:
            continue
        if not got.nullable_explicit:
            violations.append(
                f"NULLABLE_IMPLICIT: {col} expected_nullable={exp.nullable} got_nullable_implicit model_line={got.line_no}"
            )
        if exp.nullable != got.nullable:
            violations.append(
                f"NULLABLE_MISMATCH: {col} expected_nullable={exp.nullable} got_nullable={got.nullable} model_line={got.line_no}"
            )

        if exp.type_key and got.type_key and not _types_equivalent(exp.type_key, got.type_key):
            violations.append(
                f"TYPE_MISMATCH: {col} expected={exp.type_key} got={got.type_key} model_line={got.line_no}"
            )

        # Server defaults (strict, best-effort): compare when schema declares one
        if exp.default_kind:
            if not got.default_kind:
                violations.append(
                    f"MISSING_SERVER_DEFAULT: {col} expected_default={exp.default_kind}:{exp.default_value} model_line={got.line_no}"
                )
            else:
                if exp.default_kind != got.default_kind:
                    violations.append(
                        f"DEFAULT_KIND_MISMATCH: {col} expected={exp.default_kind} got={got.default_kind} model_line={got.line_no}"
                    )
                exp_v = _norm_default_value(exp.default_value)
                got_v = _norm_default_value(got.default_value)
                if exp_v and got_v and exp_v != got_v:
                    violations.append(
                        f"DEFAULT_VALUE_MISMATCH: {col} expected={exp.default_value} got={got.default_value} model_line={got.line_no}"
                    )

    return violations, model_path, expected_cols, model_cols


def _validate_constraints_profile(root: Path, table: str) -> tuple[list[str], Path]:
    schema_path = root / "docs" / "_generated" / "schema.sql"
    model_path = _find_model_path(root, table)
    schema_text = schema_path.read_text(encoding="utf-8", errors="replace")

    expected_checks = _parse_checks(schema_text, table)
    expected_uniques = _parse_unique_constraints(schema_text, table)
    expected_indexes = _parse_indexes(schema_text, table)

    parsed = _parse_model_constraints(model_path, table)
    model_checks = parsed["checks"]
    model_uniques = parsed["uniques"]
    model_indexes = parsed["indexes"]

    violations: list[str] = []

    def _missing_extra(prefix: str, expected_map: dict, model_map: dict) -> None:
        expected_names = set(expected_map.keys())
        model_names = set(model_map.keys())
        for name in sorted(expected_names - model_names):
            violations.append(f"MISSING_{prefix}: {name} model_line=None")
        for name in sorted(model_names - expected_names):
            line_no = getattr(model_map[name], "line_no", None)
            violations.append(f"EXTRA_{prefix}: {name} model_line={line_no}")

    _missing_extra("CHECK", expected_checks, model_checks)
    _missing_extra("UNIQUE", expected_uniques, model_uniques)
    _missing_extra("INDEX", expected_indexes, model_indexes)

    for name in sorted(set(expected_indexes.keys()) & set(model_indexes.keys())):
        exp = expected_indexes[name]
        got = model_indexes[name]
        if exp.unique != got.unique:
            violations.append(
                f"INDEX_UNIQUE_MISMATCH: {name} expected_unique={exp.unique} got_unique={got.unique} model_line={got.line_no}"
            )
        exp_where = re.sub(r"\s+", " ", (exp.where or "").strip()) or None
        got_where = re.sub(r"\s+", " ", (got.where or "").strip()) or None
        if exp_where != got_where:
            violations.append(
                f"INDEX_WHERE_MISMATCH: {name} expected_where={exp_where} got_where={got_where} model_line={got.line_no}"
            )

    return violations, model_path


def _validate_strict_profile(root: Path, table: str) -> int:
    # Strict profile: fk + columns/types/nullable + constraints/defaults
    fk_exit = _validate_fk_profile(root, table)
    if fk_exit != 0:
        return fk_exit

    violations, model_path, expected_cols, model_cols = _validate_columns_nullable_profile(root, table)
    constraint_violations, constraint_model_path = _validate_constraints_profile(root, table)
    violations.extend(constraint_violations)

    if violations:
        print(f"[FAIL] model_requirements strict profile violations (table={table})")
        print(f"[INFO] model_path={model_path}")
        if constraint_model_path != model_path:
            print(f"[INFO] constraints_model_path={constraint_model_path}")
        for v in violations:
            print(f"  - {v}")
        return EXIT_REQUIREMENTS_VIOLATION

    print(f"[OK] model_requirements strict profile passed (table={table})")
    print(f"[INFO] model_path={model_path}")
    print(f"[INFO] column_count={len(expected_cols)}")
    print(f"[INFO] model_column_count={len(model_cols)}")
    return 0


def _validate_lenient_profile(root: Path, table: str) -> int:
    fk_violations, model_path, fk_count = _collect_fk_violations(root, table)
    col_violations, _, expected_cols, model_cols = _validate_columns_nullable_profile(root, table)
    constraint_violations, _ = _validate_constraints_profile(root, table)

    all_violations = fk_violations + col_violations + constraint_violations
    exceptions = _load_lenient_exceptions(root)
    remaining, applied = _apply_lenient_exceptions(all_violations, table, model_path, exceptions)

    if remaining:
        print(f"[FAIL] model_requirements lenient profile violations (table={table})")
        print(f"[INFO] model_path={model_path}")
        print(f"[INFO] exceptions_loaded={len(exceptions)} applied={len(applied)}")
        for v in remaining:
            print(f"  - {v}")
        return EXIT_REQUIREMENTS_VIOLATION

    print(f"[OK] model_requirements lenient profile passed (table={table})")
    print(f"[INFO] model_path={model_path}")
    print(f"[INFO] fk_count={fk_count}")
    print(f"[INFO] column_count={len(expected_cols)}")
    print(f"[INFO] model_column_count={len(model_cols)}")
    print(f"[INFO] exceptions_loaded={len(exceptions)} applied={len(applied)}")
    if applied:
        print("[INFO] lenient_exceptions_applied:")
        for v, exc in applied:
            reason = str(exc.get("reason", "")).strip() or "(no reason)"
            print(f"  - {v} | reason={reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="HB Track: validate model vs schema.sql (SSOT)."
    )
    p.add_argument("--table", required=True, help="Table name (required, non-empty)")
    p.add_argument("--profile", choices=["fk", "strict", "lenient"], default="strict")
    args = p.parse_args(argv)
    
    # Validate --table is non-empty string (argparse doesn't enforce this)
    if not args.table or not args.table.strip():
        p.error("--table must be a non-empty string")

    # Root calculation: __file__ is now in scripts/checks/models/
    # parents[0] = scripts/checks/models, parents[1] = scripts/checks, 
    # parents[2] = scripts, parents[3] = repo_root
    root = Path(__file__).resolve().parents[3]

    if args.profile == "fk":
        return _validate_fk_profile(root, args.table)

    if args.profile == "strict":
        return _validate_strict_profile(root, args.table)

    if args.profile == "lenient":
        return _validate_lenient_profile(root, args.table)

    print(
        f"[FAIL] model_requirements profile not implemented yet "
        f"(table={args.table}, profile={args.profile})"
    )
    return EXIT_REQUIREMENTS_VIOLATION


if __name__ == "__main__":
    raise SystemExit(main())