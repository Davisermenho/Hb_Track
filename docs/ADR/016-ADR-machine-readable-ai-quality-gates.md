# ADR-016: Machine-Readable Documentation & AI Quality Gates

**Status:** Proposta  
**Data:** 2025-01-XX  
**Autores:** [Nome do autor]  
**Contexto:** HB TRACK — Governança de código com agentes de IA  
**Módulos afetados:** Todos (infraestrutura de governança)  
**Tags:** `governance`, `ai`, `quality`, `automation`, `ssot`
---

## Contexto

### Problema

Atualmente, o sistema HB TRACK possui:
- Documentação canônica para humanos (`docs/_canon/QUALITY_METRICS.md`, ADRs, workflows) em formato narrativo (Markdown).
- Agentes de IA (Copilot, revisores automáticos, scripts de validação) que precisam consumir regras, thresholds e workflows de forma determinística.
- Risco de **drift** entre documentação humana e comportamento automatizado (scripts interpretam regras de forma inconsistente).
- Falta de **validação automática** que garanta que código submetido respeita métricas de qualidade antes do merge.
- Prompts e instruções para agentes espalhados em múltiplos formatos (XML, Markdown, comentários inline) sem precedência clara.

**Exemplos concretos do problema:**

1. **Inconsistência de thresholds:**  
   `QUALITY_METRICS.md` diz "complexidade ciclomática máxima: 6", mas script de CI usa valor hardcoded `8` — código é aprovado indevidamente.

2. **Falta de contrato formal para agentes:**  
   Agent revisor de código não tem schema validado de entrada/saída (ACK/ASK/INVOCATION) — falha silenciosamente ou alucina comportamentos.

3. **Duplicação manual:**  
   Desenvolvedores copiam/colam métricas em múltiplos lugares (pre-commit hooks, CI scripts, docs) — quando mudam um threshold, esquecem de atualizar outros.

4. **Prompt drift:**  
   Prompts de agentes são copiados manualmente; variações entre desenvolvedores causam resultados inconsistentes em code reviews.
---

## Decisão

Implementaremos **documentação machine-readable** como **Single Source of Truth (SSOT)** para:
- Métricas de qualidade e thresholds (quality gates)
- Comandos aprovados (whitelist)
- Workflows canônicos (steps + conditions)
- Contratos de agentes (ACK/ASK/INVOCATION schemas)
- Guardrails (security/edit policies)

### Estrutura adotada

Criamos nova estrutura em `docs/_ai/` separada da documentação canônica para humanos:

```
docs/_ai/
├── _context/           # Entry points compactos e citáveis (AI_CONTEXT.md, ssot-precedence.yml)
├── _specs/             # Specs formais (agent-spec.json, quality-gates.yml, workflows.yml)
├── _schemas/           # JSON Schemas para validação automática
├── _prompts/           # Prompts prontos (system messages, handshake templates)
├── _maps/              # Índices/mapas (ADR index, troubleshooting, routing)
├── _guardrails/        # Políticas hard (security, edit, repo-specific rules)
└── _checklists/        # Checklists executáveis (models, parity, invariants)
```

### Formatos obrigatórios

| Artefato | Formato | Validação | Enforcement |
|----------|---------|-----------|-------------|
| Quality Gates | YAML (`quality-gates.yml`) | JSON Schema + CI | Hard (bloqueia merge) |
| Agent Contract | JSON (`agent-spec.json`) | JSON Schema | Hard (validação pré-invoke) |
| Workflows | YAML (`workflows.yml`) | JSON Schema | Soft (recomendações) |
| Approved Commands | YAML (`approved-commands.yml`) | Whitelist checker | Hard (bloqueia comandos não aprovados) |
| SSOT Precedence | YAML (`ssot-precedence.yml`) | Manual review | Hard (resolve conflitos) |
| Security/Edit Policies | YAML | JSON Schema | Hard (agentes respeitam limites) |

### Princípios obrigatórios

1. **Separação humano/IA:**  
   - Docs canônicos (`docs/_canon/`, `ADR/`) permanecem narrativos para humanos.
   - Docs AI (`docs/_ai/`) são compactos, parseáveis, validáveis.

2. **SSOT derivado:**  
   - Arquivos AI são **gerados automaticamente** a partir da documentação canônica via scripts (`docs/scripts/_ia/extractors/`).
   - Desenvolvedores editam apenas SSOT canônico; CI regenera AI docs e falha se houver drift.

3. **Validação obrigatória (CI):**  
   - Todo PR executa validadores (`docs/scripts/_ia/validators/`) que checam:
     - Sincronização SSOT ↔ AI docs
     - Schemas válidos (agent-spec, quality-gates)
     - Código respeita thresholds (radon, lizard)
     - Comandos usados estão na whitelist

4. **Handshake obrigatório para agentes:**  
   - Todo agente deve executar ACK (citar ROLE_TOKEN + regras principais) antes de agir.
   - Sem ACK correto, agente não prossegue (evita alucinação).

5. **Immutability de regions autogen:**  
   - Regiões `# HB-AUTOGEN:BEGIN/END` não podem ser editadas por agentes (enforcement via `.aiignore` e edit-policy.yml).

---

## Rationale (Por quê esta ADR é necessária)

### 1. **Padronização do diálogo humano-IA**

**Problema sem ADR:**  
Prompts espalhados em múltiplos formatos (XML inline, Markdown, comentários), cada desenvolvedor usa versão diferente.

**Solução com ADR:**  
YAML/JSON como "fonte da verdade" para métricas/workflows. Agentes leem do mesmo lugar; humanos editam SSOT e scripts regeneram AI docs.

---

### 2. **Manutenibilidade e rastreabilidade**

**Problema sem ADR:**  
Se decidirmos mudar complexidade ciclomática de 6 → 8, precisamos:
- Atualizar `QUALITY_METRICS.md`
- Atualizar script CI (`check_quality_gates.py`)
- Atualizar pre-commit hooks
- Avisar desenvolvedores
- Esperar que todos sincronizem

**Risco:** Alguém esquece um passo; threshold fica inconsistente.

**Solução com ADR:**  
1. Editar `docs/_canon/QUALITY_METRICS.md` (SSOT).
2. Executar `python docs/scripts/_ia/extractors/extract-quality-gates.py`.
3. CI valida `quality-gates.yml` contra schema.
4. Scripts de validação leem `quality-gates.yml` automaticamente.
5. ADR documenta **por quê** mudamos de 6 → 8 (contexto histórico).

**Benefício:** Uma única mudança; rastreabilidade via Git + ADR.
---

### 3. **Contrato de automação (quality gates enforcement)**

**Problema sem ADR:**  
Código com complexidade 10 entra em `main` porque CI não validou (ou threshold estava errado).

**Solução com ADR:**  
- ADR estabelece: **nenhum código entra em `main` sem passar validação automática que lê `quality-gates.yml`**.
- CI workflow (`quality-gates.yml`) executa `validate-quality-gates.py` (lê thresholds de `docs/_ai/_specs/quality-gates.yml`).
- Se código viola threshold: **PR bloqueado** (status check fail).

**Enforcement:**
```yaml
# .github/workflows/quality-gates.yml
- name: Run quality gates
  run: python .github/scripts/check_quality_gates.py --base ${{ github.event.pull_request.base.sha }} --head ${{ github.event.pull_request.head.sha }}
```

---

### 4. **Evitar alucinação de agentes (guardrails formais)**
Problema sem ADR:
Agent revisor sugere usar eval() ou logar PII porque não há guardrails formais.

**Solução com ADR:**  
- `docs/_ai/_guardrails/security-policy.yml` lista proibições explícitas:
  ```yaml
  prohibitions:
- pattern: "eval"
    severity: blocker
    message: "Proibido eval/exec — usar ast.literal_eval ou alternativa segura"
- pattern: "log.*password|log.*cpf"
    severity: blocker
    message: "Proibido logar PII — usar apenas UUID técnico"
- Agent lê `security-policy.yml` antes de sugerir mudanças.
- CI valida que código não contém patterns proibidos.
---

### 5. **Portabilidade multi-tool (Copilot, Cursor, Aider, etc.)**

**Problema sem ADR:**  
Cada ferramenta AI usa formato próprio (`.cursorrules`, Copilot instructions inline).

**Solução com ADR:**  
- `.aiprompt` (raiz repo) aponta para `docs/_ai/_INDEX.md`.

Todas as ferramentas leem mesma estrutura.
Migrar de Copilot → Cursor não exige reescrever docs.

## Consequências

### Positivas

✅ **Determinismo:**  
Mesmos inputs → mesmas métricas → mesmas ações (humanos e agentes).

✅ Automação segura:
CI valida código contra SSOT antes de merge; reduz revisão manual de métricas.

✅ Rastreabilidade:
Git history + ADRs documentam por quê mudamos thresholds/workflows.

✅ Onboarding:
Novos desenvolvedores/agentes leem AI_CONTEXT.md (3 frases) e quality-gates.yml — contexto completo em <2 min.

✅ Redução de drift:
Scripts regeneram AI docs automaticamente; CI falha se SSOT e AI docs divergirem.

### Negativas / Tradeoffs

⚠️ **Overhead inicial:**  
Criar estrutura docs/_ai/, extractors, validators, schemas — estimativa: 2–3 dias de setup.

Mitigação: Scripts reutilizáveis; benefício cresce com tamanho do projeto.

⚠️ Manutenção de schemas:
JSON Schemas precisam ser atualizados quando estrutura de agent-spec.json muda.

Mitigação: Schemas versionados (version: "1.0"); mudanças exigem ADR.

⚠️ Complexidade para contribuidores:
Desenvolvedores precisam entender fluxo: editar SSOT → regenerar AI docs → validar.

Mitigação: Documentar em docs/_ai/README.md; CI automatiza regeneração quando possível.

⚠️ Dependência de ferramentas:
Scripts usam radon, lizard, jsonschema — se bibliotecas mudarem API, scripts quebram.

Mitigação: Fixar versões em requirements.txt; testes de integração validam scripts.

## Alternativas consideradas

### Alternativa 1: Manter tudo em Markdown narrativo

**Rejeição:**  

Difícil parsear Markdown para extrair thresholds programaticamente.
Inconsistências entre docs e scripts (drift inevitável).
Alternativa 2: Hardcoded thresholds em scripts CI
Rejeição:

Não há rastreabilidade (por quê mudamos complexity de 6 → 8?).
Desenvolvedores não veem thresholds facilmente (buried in Python code).
Alternativa 3: Usar SonarQube/CodeClimate como SSOT
Rejeição:

Vendor lock-in (dependência de serviço externo).
Thresholds ficam em UI, não versionados com código.
Dificulta agents locais/offline lerem regras.
Nota: É possível integrar SonarQube além desta estrutura (importar quality-gates.yml para Sonar).

Alternativa 4: Misturar docs humanas e AI na mesma pasta
Rejeição:

Confunde propósito (narrativa vs parseable).
Agentes gastam tokens lendo prosa longa; humanos se perdem em YAMLs técnicos.
## Implementação

### Fase 1: Setup estrutura (P0 — Sprint atual)

- [ ] Criar `docs/_ai/` com subpastas (`_context`, `_specs`, `_schemas`, `_prompts`, `_maps`, `_guardrails`, `_checklists`)
- [ ] Criar `docs/scripts/_ia/` com subpastas (`extractors`, `validators`, `generators`, `agents`, `utils`)
- [ ] Criar arquivos P0:
- [ ] `docs/_ai/_context/AI_CONTEXT.md`
- [ ] `docs/_ai/_specs/quality-gates.yml`
- [ ] `docs/_ai/_specs/agent-spec.json`
- [ ] `docs/_ai/_schemas/agent-spec.schema.json`
- [ ] `docs/_ai/_schemas/quality-gates.schema.json`
- [ ] `docs/_ai/.aiignore`
- [ ] `.github/.copilotignore`
- [ ] `.aiprompt`

### Fase 2: Extractors e validadores (P1 — Próxima sprint)
- [ ] `docs/scripts/_ia/extractors/extract-quality-gates.py`
- [ ] `docs/scripts/_ia/extractors/extract-ai-context.py`
- [ ] `docs/scripts/_ia/validators/validate-ai-docs-sync.py`
- [ ] `docs/scripts/_ia/validators/validate-quality-gates.py`
- [ ] `.github/workflows/ai-docs-validation.yml`
- [ ] `.github/workflows/quality-gates.yml`

### Fase 3: Checklists e workflows (P2 — Backlog)
- [ ] `docs/_ai/_specs/workflows.yml`
- [ ] `docs/_ai/_checklists/checklist-models.yml`
- [ ] `docs/_ai/_maps/adr-index.json`
- [ ] `docs/scripts/_ia/generators/generate-ai-index.py`

### Fase 4: Integração com agentes (P2 — Backlog)
- [ ] `docs/scripts/_ia/agents/code-review-agent.py`
- [ ] Testar Copilot Chat com `AI_CONTEXT.md` + `agent-spec.json`
- [ ] Validar `quality-gates.yml` em PRs reais

## Critérios de sucesso (DoD)

### Técnicos

- [ ] CI valida `quality-gates.yml` contra schema em todo PR
- [ ] CI executa validate-quality-gates.py e bloqueia merge se código viola thresholds
- [ ] Extractors regeneram AI docs sem erros (exit 0)
- [ ] Agentes executam ACK citando ROLE_TOKEN correto antes de agir
- [ ] .aiignore e .copilotignore impedem leitura de __pycache__, _scratch/, secrets

### Processuais

- [ ] Desenvolvedores conseguem rodar python `docs/scripts/_ia/validators/validate-ai-docs-sync.py` localmente
- [ ] Documentação (docs/_ai/README.md) explica fluxo: editar SSOT → regenerar → validar
- [ ] PRs incluem checklist: "Validei quality gates localmente" (via PR template)

### Métricas

- **Baseline (antes ADR):**  
  - Violações de complexidade > 6 detectadas: ~15% dos PRs (manual review)
  - Drift entre QUALITY_METRICS.md e CI scripts: 3 inconsistências conhecidas
  - Target (3 meses após ADR):

Violações detectadas automaticamente: 100% (CI bloqueia)
Drift SSOT ↔ AI docs: 0 (CI valida)
Tempo médio code review: -20% (automação reduz revisão manual de métricas)

## Referências

- [ADR-001: SSOT Precedência](001-ADR-TRAIN-ssot-precedencia.md)
- [ADR-008: Governança por Artefatos](008-ADR-governanca-por-artefatos.md)
- [docs/_canon/01_AUTHORITY_SSOT.md](docs/_canon/01_AUTHORITY_SSOT.md)
- [docs/_canon/QUALITY_METRICS.md](docs/_canon/QUALITY_METRICS.md)
- [docs/_ai/_INDEX.md](docs/_ai/_INDEX.md) (a ser criado)
- [JSON Schema spec](https://json-schema.org/)
- [Radon documentation](https://radon.readthedocs.io/)
- [Lizard documentation](https://github.com/terryyin/lizard)



**Histórico de revisões**
Data	Versão	Autor	Mudanças
2025-01-XX	0.1	[Autor]	Proposta inicial
Aprovação
Revisor técnico: [Nome]
Aprovador: [Nome]
Data aprovação: [YYYY-MM-DD]
Status final: Proposta → Aceita (após implementação Fase 1)



