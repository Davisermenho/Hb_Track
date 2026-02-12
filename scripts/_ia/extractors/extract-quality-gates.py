#!/usr/bin/env python3
"""
extract-quality-gates.py

Descrição:
Converte docs/_canon/QUALITY_METRICS.md → docs/_ai/_specs/quality-gates.yml
Propósito: Extrair métricas de qualidade (LOC, complexidade, etc) em YAML estruturado para CI.
Entrada: docs/_canon/QUALITY_METRICS.md
Saída: docs/_ai/_specs/quality-gates.yml
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML not installed. Run: pip install PyYAML>=6.0.1", file=sys.stderr)
    sys.exit(1)


def extract_quality_gates(source_path: Path) -> dict:
    """Extract quality gate thresholds from QUALITY_METRICS.md."""
    
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}", file=sys.stderr)
        return None
    
    print(f"[INFO] Reading source file: {source_path}")
    content = source_path.read_text(encoding='utf-8')
    
    # Extract thresholds using regex patterns
    # Pattern for complexity: ### 1. Complexidade Ciclomática ... **Limite:** ≤ 6
    complexity_match = re.search(
        r'###\s*1\.\s*Complexidade Ciclomática.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content,
        re.DOTALL | re.MULTILINE
    )
    complexity_max = int(complexity_match.group(1)) if complexity_match else None
    if complexity_max:
        print(f"[INFO] Extracted complexity_max: {complexity_max}")
    else:
        print("[ERROR] Failed to extract complexity_max from QUALITY_METRICS.md", file=sys.stderr)
    
    # Pattern for nesting: ### 2. Profundidade de Aninhamento ... **Limite:** ≤ 3
    nesting_match = re.search(
        r'###\s*2\.\s*Profundidade de Aninhamento.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content,
        re.DOTALL | re.MULTILINE
    )
    nesting_max = int(nesting_match.group(1)) if nesting_match else None
    if nesting_max:
        print(f"[INFO] Extracted nesting_max: {nesting_max}")
    else:
        print("[ERROR] Failed to extract nesting_max from QUALITY_METRICS.md", file=sys.stderr)
    
    # Pattern for LOC: ### 3. Tamanho de Função/Método ... **Limite:** ≤ 50
    loc_match = re.search(
        r'###\s*3\.\s*Tamanho de Função/Método.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content,
        re.DOTALL | re.MULTILINE
    )
    loc_max = int(loc_match.group(1)) if loc_match else None
    if loc_max:
        print(f"[INFO] Extracted loc_max: {loc_max}")
    else:
        print("[ERROR] Failed to extract loc_max from QUALITY_METRICS.md", file=sys.stderr)
    
    # Pattern for params: ### 4. Número de Parâmetros ... **Limite:** ≤ 4
    params_match = re.search(
        r'###\s*4\.\s*Número de Parâmetros.*?\*\*Limite:\*\*\s*≤\s*(\d+)',
        content,
        re.DOTALL | re.MULTILINE
    )
    params_max = int(params_match.group(1)) if params_match else None
    if params_max:
        print(f"[INFO] Extracted params_max: {params_max}")
    else:
        print("[ERROR] Failed to extract params_max from QUALITY_METRICS.md", file=sys.stderr)
    
    # Check if all required thresholds were extracted
    if None in [complexity_max, nesting_max, loc_max, params_max]:
        print("[ERROR] Failed to extract all required thresholds", file=sys.stderr)
        return None
    
    # Build the output structure
    gates_spec = {
        'version': '1.0.0',
        'source': {
            'file': str(source_path.relative_to(Path.cwd())).replace('\\', '/'),
            'generated_at': datetime.now(timezone.utc).isoformat()
        },
        'gates': {
            'complexity_max': complexity_max,
            'nesting_max': nesting_max,
            'loc_max': loc_max,
            'params_max': params_max
        }
    }
    
    # Extract optional thresholds
    # Pattern for duplication: ### 6. Duplicação de Código ... **Limite:** ≤ 3%
    duplication_match = re.search(
        r'###\s*6\.\s*Duplicação de Código.*?\*\*Limite:\*\*\s*≤\s*(\d+)%',
        content,
        re.DOTALL | re.MULTILINE
    )
    if duplication_match:
        gates_spec['gates']['duplication_max'] = int(duplication_match.group(1))
        print(f"[INFO] Extracted duplication_max: {duplication_match.group(1)}")
    
    # Pattern for coverage: ### 5. Cobertura de Testes
    # Note: QUALITY_METRICS.md has multiple thresholds (95% critical, 85% business logic, 75% general)
    # The extractor captures the highest (most stringent) threshold for critical code
    coverage_match = re.search(
        r'###\s*5\.\s*Cobertura de Testes.*?≥\s*(\d+)%',
        content,
        re.DOTALL | re.MULTILINE
    )
    if coverage_match:
        gates_spec['gates']['coverage_min'] = int(coverage_match.group(1))
        print(f"[INFO] Extracted coverage_min: {coverage_match.group(1)}")
    
    return gates_spec


def main():
    """Main extraction logic."""
    # Define paths relative to repo root
    repo_root = Path.cwd()
    source_path = repo_root / 'docs' / '_canon' / 'QUALITY_METRICS.md'
    output_path = repo_root / 'docs' / '_ai' / '_specs' / 'quality-gates.yml'
    
    print("[INFO] Starting quality gates extraction")
    print(f"[INFO] Source: {source_path}")
    print(f"[INFO] Output: {output_path}")
    
    # Extract gates
    gates_spec = extract_quality_gates(source_path)
    if gates_spec is None:
        print("[ERROR] Extraction failed", file=sys.stderr)
        sys.exit(1)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write YAML output
    print(f"[INFO] Writing output to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(gates_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print("[SUCCESS] Quality gates extracted successfully")
    print(f"[INFO] Generated: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
