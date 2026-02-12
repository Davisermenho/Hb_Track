#!/usr/bin/env python3
"""
extract-quality-gates.py

Descrição:
Converte docs/_canon/QUALITY_METRICS.md → docs/_ai/_specs/quality-gates.yml
Propósito: Extrair métricas de qualidade (complexidade, aninhamento, etc) em YAML estruturado para CI.
Entrada: docs/_canon/QUALITY_METRICS.md
Saída: docs/_ai/_specs/quality-gates.yml
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed. Run: pip install PyYAML>=6.0.1", file=sys.stderr)
    sys.exit(1)


# Hardcoded fallback values (from QUALITY_METRICS.md)
FALLBACK_VALUES = {
    "complexity_max": 6,
    "nesting_max": 3,
    "function_lines_max": 50,
    "parameters_max": 4
}


def extract_thresholds_from_markdown(md_path: Path) -> dict:
    """
    Parse QUALITY_METRICS.md to extract threshold values.
    
    Uses regex patterns to find:
    - Complexidade Ciclomática: **Limite:** ≤ 6
    - Profundidade de Aninhamento: **Limite:** ≤ 3 níveis
    - Tamanho de Função/Método: **Limite:** ≤ 50 linhas
    - Número de Parâmetros: **Limite:** ≤ 4 parâmetros
    """
    if not md_path.exists():
        return {}
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except IOError as e:
        print(f"[WARN] Failed to read {md_path}: {e}", file=sys.stderr)
        return {}
    
    thresholds = {}
    
    # Pattern for "**Limite:** ≤ N" (matches markdown bold with specific format)
    
    # 1. Complexidade Ciclomática
    complexity_match = re.search(
        r'###\s+1\.\s+Complexidade\s+Ciclomática.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content, re.IGNORECASE | re.DOTALL
    )
    if complexity_match:
        thresholds['complexity_max'] = int(complexity_match.group(1))
    
    # 2. Profundidade de Aninhamento
    nesting_match = re.search(
        r'###\s+2\.\s+Profundidade\s+de\s+Aninhamento.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content, re.IGNORECASE | re.DOTALL
    )
    if nesting_match:
        thresholds['nesting_max'] = int(nesting_match.group(1))
    
    # 3. Tamanho de Função/Método
    function_lines_match = re.search(
        r'###\s+3\.\s+Tamanho\s+de\s+Função.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content, re.IGNORECASE | re.DOTALL
    )
    if function_lines_match:
        thresholds['function_lines_max'] = int(function_lines_match.group(1))
    
    # 4. Número de Parâmetros
    parameters_match = re.search(
        r'###\s+4\.\s+Número\s+de\s+Parâmetros.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content, re.IGNORECASE | re.DOTALL
    )
    if parameters_match:
        thresholds['parameters_max'] = int(parameters_match.group(1))
    
    return thresholds


def generate_quality_gates_yaml(source_path: Path, allow_fallback: bool = True) -> dict:
    """
    Generate quality gates specification from source markdown.
    
    Args:
        source_path: Path to QUALITY_METRICS.md
        allow_fallback: If True, use hardcoded values when parsing fails
    
    Returns:
        Dictionary containing quality gates specification
    """
    # Extract thresholds from markdown
    extracted = extract_thresholds_from_markdown(source_path)
    
    # Build gates using extracted values or fallbacks
    gates = {}
    missing_keys = []
    
    for key, fallback_value in FALLBACK_VALUES.items():
        if key in extracted:
            gates[key] = extracted[key]
        elif allow_fallback:
            gates[key] = fallback_value
            missing_keys.append(key)
        else:
            raise ValueError(f"Missing required threshold: {key} (use --allow-fallback to use defaults)")
    
    if missing_keys and allow_fallback:
        print(f"[WARN] Using fallback values for: {', '.join(missing_keys)}", file=sys.stderr)
    
    # Build complete specification
    spec = {
        "version": "1.0.0",
        "source": str(source_path.absolute()),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "gates": gates
    }
    
    return spec


def main():
    """Main extraction logic."""
    parser = argparse.ArgumentParser(
        description="Extract quality gates from QUALITY_METRICS.md to YAML"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("docs/_canon/QUALITY_METRICS.md"),
        help="Path to source markdown file (default: docs/_canon/QUALITY_METRICS.md)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/_ai/_specs/quality-gates.yml"),
        help="Path to output YAML file (default: docs/_ai/_specs/quality-gates.yml)"
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        default=False,
        help="Use hardcoded fallback values when parsing fails"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output to stdout without writing file"
    )
    
    args = parser.parse_args()
    
    # Validate source file exists
    if not args.source.exists():
        print(f"[ERROR] Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)
    
    # Generate specification
    try:
        spec = generate_quality_gates_yaml(args.source, args.allow_fallback)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    
    # Convert to YAML
    yaml_output = yaml.safe_dump(spec, default_flow_style=False, sort_keys=False)
    
    # Dry run or write file
    if args.dry_run:
        print(yaml_output)
    else:
        # Ensure output directory exists
        args.output.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(yaml_output)
            print(f"✅ Generated: {args.output}")
        except IOError as e:
            print(f"[ERROR] Failed to write output: {e}", file=sys.stderr)
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
