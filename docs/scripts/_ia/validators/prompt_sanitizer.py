#!/usr/bin/env python3
"""
HB Track Prompt Sanitizer

Transforms loose prompts into deterministic prompts by:
- Replacing conversational language with formal language
- Converting hedging words to RFC 2119 keywords
- Removing opinions and promotional language
- Enforcing canonical terminology

Usage:
    python prompt_sanitizer.py "texto ambíguo"
    python prompt_sanitizer.py --interactive "texto"

Version: 1.0.0
Last Updated: 2026-02-13
"""

import sys
import re

# Replacement rules (from AGENT_DRIFT_RULES.md)
REPLACEMENTS = {
    # Conversational → Formal
    "acho que": "",
    "I think": "",
    "na minha opinião": "",
    "in my opinion": "",
    "podemos": "the system can",
    "we can": "the system can",
    "seria legal": "the system should",
    "it would be nice": "the system should",
    
    # Hedging → Normative
    "talvez": "potentially",
    "maybe": "potentially",
    "pode ser que": "may",
    "might": "may",
    "provavelmente": "is expected to",
    "probably": "is expected to",
    "deveria": "MUST",
    "should consider": "SHALL",
    "é possível": "can",
    "it's possible": "can",
    "recomendo": "specification requires",
    "I recommend": "specification requires",
    
    # Promotional → Neutral
    "melhor": "canonical",
    "best": "canonical",
    "ideal": "deterministic",
    "perfeito": "compliant",
    "perfect": "compliant",
    
    # Action verbs → Formal (only unambiguous replacements)
    "implementar": "formalize",
    "criar": "define",
}

# Case-insensitive patterns for whole-word replacement
PATTERNS = {
    re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE): v
    for k, v in REPLACEMENTS.items()
}


def sanitize(text: str) -> str:
    """Apply sanitization rules to text."""
    original = text
    
    # Apply replacements
    for pattern, replacement in PATTERNS.items():
        text = pattern.sub(replacement, text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def sanitize_interactive(text: str) -> str:
    """Apply sanitization with user confirmation for each replacement."""
    result = text
    changes = []
    
    for pattern, replacement in PATTERNS.items():
        matches = list(pattern.finditer(result))
        if not matches:
            continue
        
        print(f"\nFound: '{matches[0].group()}'")
        print(f"Replace with: '{replacement}'")
        response = input("Apply? [y/N]: ").strip().lower()
        
        if response == 'y':
            result = pattern.sub(replacement, result)
            changes.append((matches[0].group(), replacement))
    
    if changes:
        print("\n" + "=" * 60)
        print("Applied changes:")
        for old, new in changes:
            print(f"  '{old}' → '{new}'")
    
    return result


def main():
    """Main sanitizer CLI."""
    if len(sys.argv) < 2:
        print("Usage: prompt_sanitizer.py [--interactive] <text>")
        print("\nExamples:")
        print('  python prompt_sanitizer.py "crie a melhor arquitetura"')
        print('  python prompt_sanitizer.py --interactive "acho que podemos implementar"')
        sys.exit(1)
    
    interactive = False
    if sys.argv[1] == "--interactive":
        interactive = True
        text = " ".join(sys.argv[2:])
    else:
        text = " ".join(sys.argv[1:])
    
    if not text.strip():
        print("[ERROR] Empty input text", file=sys.stderr)
        sys.exit(1)
    
    print("Original:")
    print(f"  {text}")
    print()
    
    if interactive:
        sanitized = sanitize_interactive(text)
    else:
        sanitized = sanitize(text)
    
    print("Sanitized:")
    print(f"  {sanitized}")
    
    if sanitized == text:
        print("\n[OK] No changes needed (already canonical)")
    else:
        print("\n[SANITIZED] Applied deterministic language rules")


if __name__ == "__main__":
    main()
