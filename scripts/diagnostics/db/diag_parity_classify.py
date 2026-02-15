#!/usr/bin/env python3
# HB_SCRIPT_KIND: DIAGNOSTIC
# HB_SCRIPT_SIDE_EFFECTS: FS_READ
# HB_SCRIPT_SCOPE: parity
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: python scripts/diagnostics/db/diag_parity_classify.py
# HB_SCRIPT_OUTPUTS: classification_report

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DET_RE = re.compile(r"Detected (.+)$")
WARN_RE = re.compile(r"SAWarning: (.+)$")

# Remover cores ANSI e ler com heurística de encoding (BOM / UTF-16LE fallback)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def read_log_lines(path: Path) -> List[str]:
    raw = path.read_bytes()

    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        s = raw.decode("utf-16", errors="replace")
    elif raw.startswith(b"\xef\xbb\xbf"):
        s = raw.decode("utf-8-sig", errors="replace")
    else:
        # heurística: muitos NULs no início => UTF-16LE
        if raw[:200].count(b"\x00") > 20:
            s = raw.decode("utf-16le", errors="replace")
        else:
            s = raw.decode("utf-8", errors="replace")

    # remove ANSI colors, se existirem
    s = ANSI_RE.sub("", s)

    # FIX: strip NUL bytes residuais (defesa contra encoding issues do PS 5.1)
    if "\x00" in s:
        import sys
        print(
            f"[parity_classify] WARNING: NUL bytes detectados em {path} "
            f"(provavel encoding UTF-16LE do PowerShell 5.1). Removendo.",
            file=sys.stderr,
        )
        s = s.replace("\x00", "")

    return s.splitlines()

# Regex para extrair table do nome de sequence (ex: 'athletes_id_seq' -> 'athletes')
_SEQ_NAME_RE = re.compile(r"^(\w+?)_(?:id|pk)_seq$")


def extract_table_col(msg: str) -> Dict[str, Optional[str]]:
    """
    Extrai table/column de mensagens Alembic "Detected ...".
    Patterns são aplicados do mais específico para o mais genérico;
    o último match ganha (overwrite intencional).
    """
    table: Optional[str] = None
    col: Optional[str] = None

    # --- Patterns específicos (do menos para mais específico) ---

    # "on table X" / "on table 'X'"
    m = re.search(r"on table ['\"]?([a-zA-Z0-9_]+)['\"]?", msg)
    if m:
        table = m.group(1)

    # "for '(table).(column)'" (type change)
    m = re.search(r"for ['\"]([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)['\"]?", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # Genérico: 'table.column' entre aspas simples
    m = re.search(r"'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # "column comment on column 'table.column'"
    m = re.search(r"column comment (?:on column )?'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # "added/removed column 'table.column'"
    m = re.search(r"(?:added|removed) column '([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # "NULL on column 'table.column'" / "NOT NULL on column 'table.column'"
    m = re.search(r"NULL on column '([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # "server_default on column 'table.column'" / "server default change on 'table.column'"
    m = re.search(r"server[_ ]default[^']*'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'", msg)
    if m:
        table = m.group(1)
        col = m.group(2)

    # Sequence: "sequence named 'athletes_id_seq'" -> extrair table do nome
    if table is None:
        m = re.search(r"sequence named '([a-zA-Z0-9_]+)'", msg)
        if m:
            seq_name = m.group(1)
            sm = _SEQ_NAME_RE.match(seq_name)
            if sm:
                table = sm.group(1)

    return {"table": table, "column": col}

def classify(msg: str) -> str:
    s = msg.lower()

    # comments
    if "comment" in s:
        return "comment"

    # indexes
    if " index " in s or s.startswith("added index") or s.startswith("removed index"):
        return "index"

    # constraints
    if "foreign key" in s:
        return "constraint_fk"
    if "unique constraint" in s:
        return "constraint_unique"
    if "primary key" in s:
        return "constraint_pk"

    # table/column changes
    if s.startswith("added table") or s.startswith("removed table"):
        return "table"
    if "added column" in s or "removed column" in s:
        return "column"

    # type/default/nullability
    if "type change" in s:
        return "type"
    if "null on column" in s or "not null on column" in s:
        return "nullability"
    if "server default" in s or "server_default" in s:
        return "default"

    # sequences (normalmente ruído)
    if "detected sequence" in s:
        return "sequence"

    return "other"

def is_structural(category: str) -> bool:
    return category in {
        "table", "column", "type", "nullability",
        "constraint_fk", "constraint_unique", "constraint_pk",
        "default",
        # index pode ser estrutural dependendo do seu contrato; aqui deixo como não-estrutural por padrão
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    log_path = Path(args.log)
    text = read_log_lines(log_path)

    warnings: List[Dict[str, str]] = []
    items: List[Dict[str, Any]] = []

    for line in text:
        w = WARN_RE.search(line)
        if w:
            warnings.append({"category": "sa_warning", "message": w.group(1).strip()})

        m = DET_RE.search(line)
        if not m:
            continue

        msg = m.group(1).strip()

        # Alembic informational noise: sequence ownership -> assume SERIAL (not a parity diff)
        low = msg.lower()
        if "sequence" in low and "assuming serial" in low and "omitting" in low:
            warnings.append({"category": "alembic_info", "message": msg})
            continue

        category = classify(msg)
        tc = extract_table_col(msg)

        items.append({
            "category": category,
            "structural": is_structural(category),
            "message": msg,
            **tc,
        })

    structural = [x for x in items if x["structural"]]
    non_structural = [x for x in items if not x["structural"]]

    report = {
        "summary": {
            "total": len(items),
            "structural_count": len(structural),
            "non_structural_count": len(non_structural),
            "by_category": {c: sum(1 for x in items if x["category"] == c) for c in sorted({x["category"] for x in items})},
            "warnings_count": len(warnings),
        },
        "warnings": warnings,
        "items": items,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()