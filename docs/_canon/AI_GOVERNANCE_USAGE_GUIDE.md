# HB TRACK — AI GOVERNANCE USAGE GUIDE

## 🏗️ Estrutura Criada

### Núcleo de Governança (`docs/_canon/`)

#### LEVEL 0 — Constituição
- [AI_KERNEL.md](AI_KERNEL.md) — **Constituição base** para qualquer IA

#### LEVEL 1 — Protocolos
- [LANGUAGE_PROTOCOL.md](LANGUAGE_PROTOCOL.md) — RFC 2119 + DSL
- [FAILSAFE_PROTOCOL.md](FAILSAFE_PROTOCOL.md) — Regras anti-alucinação
- [ARCH_REQUEST_DSL.md](ARCH_REQUEST_DSL.md) — Definição da linguagem formal
- [ARCHITECT_BOOTLOADER.md](ARCHITECT_BOOTLOADER.md) — Prompt inicial universal
- [ARCHITECT_HANDSHAKE.md](ARCHITECT_HANDSHAKE.md) — Handshake de projeto
- [GOVERNANCE_MODEL.md](GOVERNANCE_MODEL.md) — Hierarquia de camadas
- [AGENT_BEHAVIOR.md](AGENT_BEHAVIOR.md) — Papéis dos agentes

#### LEVEL 2-3 — Prompts & Schemas
- `docs/_canon/_prompts/` — Prompts especializados por tipo de agente
- `docs/_canon/_schemas/` — JSON schemas para validação

### Scripts de Automação (`docs/scripts/_ia/`)

1. **generate_ai_governance_index.py** — Gera índice automático
2. **lint_arch_request.py** — Valida documentos ARCH_REQUEST
3. **check_logs_compaction.py** — Verifica compactação de logs

---

## 🚀 Quick Start

### Para Agentes/IA
```bash
# Carregue o núcleo antes de qualquer operação:
Load docs/_canon/AI_KERNEL.md
```

### Para Humanos
```bash
# Gerar/atualizar índice de governança:
python docs/scripts/_ia/generate_ai_governance_index.py --write

# Verificar se índice está atualizado (CI/CD):
python docs/scripts/_ia/generate_ai_governance_index.py --check

# Validar documentos ARCH_REQUEST:
python docs/scripts/_ia/lint_arch_request.py --glob "docs/**/ARCH_REQUEST*.md"

# Verificar compactação de logs:
python docs/scripts/_ia/check_logs_compaction.py --changelog "path/changelog.md" --exec-log "path/execution_log.md"
```

---

## 📋 Integração Automática

### .github/instructions/00_general.instructions.md
✅ Atualizado com referência ao `AI_KERNEL.md`

### .github/copilot-instructions.md  
✅ Atualizado com `Source of truth: docs/_canon/AI_KERNEL.md`

### docs/_canon/AI_GOVERNANCE_INDEX.md
✅ Gerado automaticamente com hash `fb5507898a045619`

---

## 🎯 Benefícios Implementados

1. **Determinismo**: Agentes seguem constituição fixa
2. **Hierarchia Clara**: L0 > L1 > L2 > L3 precedência definida  
3. **Validação Automática**: Scripts detectam violações de DSL
4. **Rastreabilidade**: Índice auto-gerado + hash integrity
5. **Anti-Alucinação**: Protocolos de failsafe obrigatórios
6. **Separação de Papéis**: Architect/Executor/Reviewer bem definidos

---

## 💡 Próximos Passos

1. Criar documentos ARCH_REQUEST seguindo o DSL
2. Configurar CI/CD para rodar validações automáticas  
3. Expandir schemas conforme necessário
4. Treinar novos agentes com prompts específicos
