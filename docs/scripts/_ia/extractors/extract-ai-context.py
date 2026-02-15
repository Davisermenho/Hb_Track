#!/usr/bin/env python3
"""
extract-ai-context.py

Descrição:
Extrai AI_CONTEXT.md compacto de docs/_canon/00_START_HERE.md (3-5 frases + ROLE_TOKEN).
Propósito: Criar contexto persistente em memória para agents AI sem carregar 400+ linhas.
Entrada: docs/_canon/00_START_HERE.md
Saída: docs/_ai/_context/AI_CONTEXT.md (ou JSON)
"""

import json
import sys
from pathlib import Path

def extract_context():
    """TODO: Implementar extractão de frases-chave de 00_START_HERE.md"""
    pass

def main():
    """TODO: Implementar lógica principal de extração"""
    print("[TODO] extract-ai-context.py: implement context extraction from 00_START_HERE.md")
    sys.exit(0)

if __name__ == "__main__":
    main()
