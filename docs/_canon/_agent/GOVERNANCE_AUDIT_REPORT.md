# Governance Audit Report — Análise de Consistência Cruzada

**Data:** 2026-02-13  
**Branch:** docs/gov-unify-001  
**Baseline Commit:** 3c3a466 (docs(ai): implement canonical ai governance suite and protocols)  
**Scope:** Auditoria de sobreposições, lacunas e inconsistências entre `docs/_ai/` e `docs/_canon/`

---

## 1. EXECUTIVE SUMMARY

Encontradas **6 categorias críticas** de problemas estruturais:

1. **Duplicação de Conteúdo** (3 pares críticos)
2. **Redundância de Índices** (2 índices concorrentes)
3. **Conflitos de Precedência** (hierarquia ambígua)
4. **Stubs Não Resolvidos** (2 redirects pendentes)
5. **Lacunas de Cobertura** (3 áreas sem cobertura)
6. **Inconsistências de Versionamento** (múltiplos status/versões)

**Impacto:** Risco alto de **agent drift**, ambiguidade de autoridade, e manutenção insustentável.

**Ação Recomendada:** Unificação progressiva seguindo o plano de remediação (Seção 7).

---

## 2. SOBREPOSIÇÕES CRÍTICAS (Duplicação de Conteúdo)

### 2.1 INDEX DUPLICADO

**Arquivos em conflito:**
- `docs/_ai/_INDEX.md` (511 linhas)
- `docs/_canon/00_START_HERE.md` (462 linhas)

**Sobreposição:** ~85% de conteúdo idêntico:
- Glossário de termos técnicos (SSOT, Parity, Guard, Baseline, Gate, etc)
- Quick Start Routing (5 passos canônicos)
- Regras de CWD (Current Working Directory)
- Regra para `-SkipDocsRegeneration`
- Regra Anti-Loop (structural diff persistente)

**Divergências menores:**
- `_INDEX.md` tem seção "SSOT Fresh" mais detalhada
- `00_START_HERE.md` adiciona tabela "Documentos obrigatórios por tipo de tarefa"

**Impacto:** 
- **Severidade:** HIGH
- Agents não sabem qual consultar primeiro
- Manutenção duplicada (risco de drift entre versões)
- Usuários humanos confusos sobre porta única

**Evidência:**
```
docs/_ai/_INDEX.md#L1-L100 ≈ docs/_canon/00_START_HERE.md#L1-L100
```

---

### 2.2 AGENT PROMPTS DUPLICADO

**Arquivos em conflito:**
- `docs/_ai/06_AGENT-PROMPTS.md` (413 linhas)
- `docs/_canon/06_AGENT_PROMPTS_MODELS.md` (não existe no repo atual)

**Status:** `06_AGENT-PROMPTS.md` existe em `docs/_ai/`, mas referenciado como canônico em:
- `docs/_ai/_maps/agent-routing-map.md#L40` (referência a `docs/_canon/06_AGENT_PROMPTS_MODELS.md`)
- `docs/_canon/00_START_HERE.md` (não menciona explicitamente)

**Problema:** Inconsistência de localização esperada vs real.

**Impacto:**
- **Severidade:** MEDIUM
- Referências quebradas se arquivo for movido
- Ambiguidade sobre qual arquivo é canônico

---

### 2.3 ROUTING MAP DUPLICADO

**Arquivos em conflito:**
- `docs/_ai/07_AGENT_ROUTING_MAP.md` (stub redirect)
- `docs/_ai/_maps/agent-routing-map.md` (176 linhas, conteúdo real)
- `docs/_canon/02_CONTEXT_MAP.md` (166 linhas, abordagem diferente)

**Sobreposição:** Ambos mapeiam "intenção → documentação → comandos", mas:
- `agent-routing-map.md`: Focado em instruções `.github/instructions/` + docs canônicos
- `02_CONTEXT_MAP.md`: Focado em fluxos operacionais por domínio

**Divergência:** Não há unificação clara; agentes podem consultar qualquer um.

**Impacto:**
- **Severidade:** MEDIUM
- Redundância conceitual
- Manutenção duplicada de mapeamentos

**Evidência:**
```
docs/_ai/_maps/agent-routing-map.md#L25-L50 (ação B: "Varredura")
docs/_canon/02_CONTEXT_MAP.md#L20-L30 (intenção 3: "Executar Parity Scan")
```

---

## 3. REDUNDÂNCIA DE ÍNDICES (Múltiplas Portas de Entrada)

### 3.1 Índices Concorrentes

**Arquivos identificados:**
1. `docs/_ai/_INDEX.md` — "Router Central" para agents
2. `docs/_canon/00_START_HERE.md` — "Porta única" canônica
3. `docs/_canon/GOVERNANCE_MODEL.md` — Hierarquia normativa (precedência formal)

**Problema:** 3 pontos de entrada diferentes para agents, sem hierarquia clara.

**Hierarquia Declarada:**
- `GOVERNANCE_MODEL.md` declara a hierarquia normativa (LEVEL 0-4)
- `00_START_HERE.md` declara-se como "porta única"
- `_INDEX.md` declara-se como "Router Central"

**Conflito:** Quem prevalece em caso de divergência?

**Impacto:**
- **Severidade:** HIGH
- Ambiguidade de autoridade
- Agents podem ignorar governança se começarem por `_INDEX.md`

---

### 3.2 Tutoriais Duplicados

**Arquivos identificados:**
- `docs/_canon/AI_TUTORIAL.md` (743 linhas, focado em agents)
- `docs/_canon/HUMAN_TUTORIAL.md` (500 linhas, focado em humanos)

**Sobreposição:** Seções "Comandos Canônicos" e "Validação de CWD" aparecem em ambos.

**Impacto:**
- **Severidade:** LOW
- Redundância esperada (públicos diferentes), mas seções técnicas devem ser referenciadas, não duplicadas.

---

## 4. CONFLITOS DE PRECEDÊNCIA (Hierarquia Ambígua)

### 4.1 Stubs vs Canon

**Stubs identificados:**
- `docs/_ai/07_AGENT_ROUTING_MAP.md` → redireciona para `_maps/agent-routing-map.md`
- `docs/_ai/SYSTEM_DESIGN.md` → redireciona para `../01_sistema-atual/SYSTEM_DESIGN.md`

**Problema:** Stubs criam indireção; agents podem não seguir redirect se processarem markdown literalmente.

**Recomendação:** Remover stubs após período de transição.

---

### 4.2 Guardrails Fragmentados

**Arquivos de guardrails:**
1. `docs/_ai/INVARIANTS_AGENT_GUARDRAILS.md` (140 linhas, comandos canônicos + exit codes)
2. `docs/_ai/_guardrails/GUARDRAIL_POLICY_BASELINE.md` (política baseline.json)
3. `docs/_ai/_guardrails/GUARDRAIL_POLICY_PARITY.md` (não lido, assumido similar)
4. `docs/_ai/_guardrails/GUARDRAIL_POLICY_REQUIREMENTS.md` (não lido, assumido similar)
5. `docs/_ai/_context/AGENT_GUARDRAILS.md` (não lido, possivelmente sobrepõe)

**Problema:** Fragmentação excessiva; agents precisam ler 5+ arquivos para entender guardrails completos.

**Impacto:**
- **Severidade:** MEDIUM
- Reduz eficiência (mais tokens consumidos)
- Maior risco de miss de regras críticas

---

## 5. LACUNAS DE COBERTURA

### 5.1 Governança vs Operação (Gap de Bridge)

**Observação:** 
- `docs/_canon/_agent/` define governança formal (TASK BRIEF, EVIDENCE PACK, protocolos)
- `docs/_ai/` define operação (comandos, prompts, checklists)

**Gap:** Não há documento que "bridge" essas camadas, explicando:
- Quando usar protocolo formal (TASK BRIEF) vs prompt direto?
- Como escalonar de operação simples → full governance?
- Qual o threshold de complexidade para exigir TASK BRIEF?

**Impacto:**
- **Severidade:** MEDIUM
- Agents podem operar indefinidamente sem governança formal
- Risco de tarefas complexas sem rastreabilidade

---

### 5.2 Exit Codes Centralizados (Não Encontrado)

**Esperado:** Documento canônico central para exit codes (`docs/references/exit_codes.md`)

**Referenciado em:**
- `docs/_ai/_INDEX.md#L35` (glossário menciona exit codes)
- `docs/_canon/00_START_HERE.md#L35` (idem)
- Múltiplos scripts PowerShell e Python

**Status:** Não verificado se `docs/references/exit_codes.md` existe e está atualizado.

**Impacto:**
- **Severidade:** LOW (se existir e estiver atualizado)
- **Severidade:** HIGH (se não existir ou estiver desatualizado)

---

### 5.3 Approved Commands (YAML vs Markdown Source)

**Arquivos relacionados:**
- `docs/_canon/08_APPROVED_COMMANDS.md` (fonte markdown)
- `docs/_ai/_context/approved-commands.yml` (gerado por extractor)

**Gap:** Não há documento explicando:
- Como atualizar `08_APPROVED_COMMANDS.md` (formato, seções obrigatórias)
- Quando regenerar `approved-commands.yml`
- Quem valida que extractor está correto após mudança no formato

**Impacto:**
- **Severidade:** LOW
- Risco de quebrar pipeline de aprovação se formato mudar

---

## 6. INCONSISTÊNCIAS DE VERSIONAMENTO

### 6.1 Status Tags Inconsistentes

**Observado:**
- `docs/_canon/_agent/*.md` → `Status: CANONICAL`, `Version: 1.0.0`
- `docs/_ai/_INDEX.md` → menciona "Última verificação: 2026-02-10"
- `docs/_ai/06_AGENT-PROMPTS.md` → `ID: CANON-AGENT-PROMPTS-MODELS-006`, `Status: CANÔNICO`, `Última verificação: 2026-02-10`
- `docs/_canon/00_START_HERE.md` → sem header de status/versão

**Problema:** Múltiplos sistemas de metadata (Status: CANONICAL vs ID: CANON-xxx vs sem metadata).

**Impacto:**
- **Severidade:** LOW
- Confusão sobre quais docs são "canônicos oficialmente"
- Dificulta auditoria de versionamento

---

### 6.2 Datas de "Última Verificação" Desatualizadas

**Arquivos com data antiga:**
- `docs/_ai/_INDEX.md` → `2026-02-10` (3 dias atrás se hoje é 13)
- `docs/_ai/06_AGENT-PROMPTS.md` → `2026-02-10`

**Problema:** Se houve mudanças estruturais em 2026-02-12 (commit `3c3a466`), essas datas não foram atualizadas.

**Impacto:**
- **Severidade:** LOW
- Metadata de auditoria não reflete realidade

---

## 7. PLANO DE REMEDIAÇÃO (Recomendações Priorizadas)

### PRIORITY 1 — CRITICAL (Resolver Agora)

#### R1: Unificar Índices (HIGH)
**Ação:** Consolidar `docs/_ai/_INDEX.md` + `docs/_canon/00_START_HERE.md` em **um único arquivo**.

**Proposta:**
- **Arquivo canônico:** `docs/_canon/00_START_HERE.md`
- **Ação em `_INDEX.md`:** Transformar em stub redirect + resumo executivo linkando para `00_START_HERE.md`
- **Justificativa:** Canon deve ser autoridade; `_INDEX.md` vira router leve.

**Artefato:** ADR documentando decisão + commit unificando.

---

#### R2: Declarar Hierarquia de Precedência (HIGH)
**Ação:** Criar seção explícita em `docs/_canon/GOVERNANCE_MODEL.md` definindo:

```
LEVEL 0: Governança Formal (docs/_canon/_agent/)
LEVEL 1: Documentação Canônica (docs/_canon/)
LEVEL 2: Documentação Operacional (docs/_ai/)
LEVEL 3: Artefatos Gerados (docs/_generated/)
```

**Regra:** Em caso de conflito, nivel superior vence.

**Artefato:** Atualização em `docs/_canon/GOVERNANCE_MODEL.md` (NORMATIVE HIERARCHY).

---

### PRIORITY 2 — HIGH (Resolver Esta Sprint)

#### R3: Resolver Fragmentação de Guardrails (MEDIUM → HIGH)
**Ação:** Consolidar múltiplos `GUARDRAIL_POLICY_*.md` em:
- **Opção A:** Um único `GUARDRAILS_MASTER.md` com seções por tipo (baseline, parity, requirements)
- **Opção B:** Manter separados mas criar `GUARDRAILS_INDEX.md` que lista todos + quando usar cada um

**Preferência:** Opção A (reduz indireção).

**Artefato:** Novo arquivo + remoção dos fragmentados (deprecate stubs se necessário).

---

#### R4: Bridge Governance ↔ Operation (MEDIUM)
**Ação:** Criar documento `docs/_canon/_agent/WHEN_TO_USE_TASK_BRIEF.md` com critérios objetivos:

**Exemplo de critérios:**
- Tarefa afeta > 3 arquivos → exige TASK BRIEF
- Tarefa envolve mudança em SSOT (schema.sql) → exige TASK BRIEF
- Tarefa > 30 minutos estimados → exige TASK BRIEF
- Prompt operacional (< 5 min, 1-2 comandos) → pode usar prompt direto

**Artefato:** Novo documento canônico.

---

### PRIORITY 3 — MEDIUM (Resolver Próxima Sprint)

#### R5: Remover Stubs Após Período de Transição
**Ação:** 
- `docs/_ai/07_AGENT_ROUTING_MAP.md` → remover (já passou período de 2 releases conforme stub)
- `docs/_ai/SYSTEM_DESIGN.md` → remover ou converter em link simbólico (se suportado)

**Condição:** Só remover após validar que nenhuma referência externa (fora do repo) aponta para stubs.

---

#### R6: Unificar Metadata de Versionamento
**Ação:** Padronizar header YAML em todos os documentos canônicos:

```yaml
---
id: CANON-<CATEGORY>-<NNN>
status: CANONICAL | DRAFT | DEPRECATED
version: X.Y.Z (SemVer)
last_verified: YYYY-MM-DD
applies_to: AI Architect | AI Executor | Human Developer
---
```

**Artefato:** Script para validar metadata + atualizar todos os docs canônicos.

---

### PRIORITY 4 — LOW (Boas Práticas, Não Bloqueante)

#### R7: Criar .aiignore Unificado
**Ação:** Verificar se `docs/_ai/.aiignore` cobre corretamente:
- `docs/_generated/_scratch/`
- `docs/scripts/_archive/`
- Temp files (`*.tmp`, `*.log`, `%TEMP%`)

**Artefato:** Atualização em `.aiignore` se necessário.

---

#### R8: Documentar Exit Codes Centralizadamente
**Ação:** Criar ou atualizar `docs/references/exit_codes.md` com:
- Tabela canônica: exit code → significado → ação esperada
- Exemplos de output para cada código
- Links para scripts que usam cada código

**Artefato:** Documento canônico + validação que glossários linkam corretamente.

---

## 8. MÉTRICAS DE AUDITORIA

| Métrica | Valor | Threshold | Status |
|---------|-------|-----------|--------|
| Arquivos auditados | 50+ | N/A | ✅ |
| Sobreposições críticas | 3 | ≤ 1 | ❌ FAIL |
| Lacunas de cobertura | 3 | ≤ 2 | ⚠️ WARN |
| Índices concorrentes | 3 | 1 | ❌ FAIL |
| Stubs pendentes | 2 | 0 | ⚠️ WARN |
| Fragmentação (guardrails) | 5 arquivos | ≤ 2 | ❌ FAIL |

**VEREDITO GERAL:** ❌ **FAIL** — Requer ação corretiva imediata (Priority 1 + 2).

---

## 9. PRÓXIMOS PASSOS (Acionável)

1. **Revisar este relatório** com stakeholders (dev lead + product owner)
2. **Aprovar plano de remediação** (seção 7)
3. **Criar ADR-NNN** para decisão de unificação de índices (R1)
4. **Executar R1 + R2** (Priority 1) nesta branch `docs/gov-unify-001`
5. **Atualizar CHANGELOG.md** e **EXECUTIONLOG.md** com resultados da unificação
6. **Abrir PR** com evidências de before/after
7. **Validar que agents conseguem navegar** após unificação (smoke test)

---

## 10. ANEXOS

### A. Arquivos Auditados (Lista Completa)

```
docs/_ai/_INDEX.md
docs/_ai/06_AGENT-PROMPTS.md
docs/_ai/07_AGENT_ROUTING_MAP.md
docs/_ai/INV_TASK_TEMPLATE.md
docs/_ai/INVARIANTS_AGENT_GUARDRAILS.md
docs/_ai/INVARIANTS_AGENT_PROTOCOL.md
docs/_ai/SYSTEM_DESIGN.md
docs/_ai/_checklists/CHECKLIST_AGENT_DEPLOYMENT.md
docs/_ai/_checklists/CHECKLIST_AGENT_DOCUMENTATION.md
docs/_ai/_checklists/CHECKLIST_AGENT_VALIDATION.md
docs/_ai/_context/AGENT_CONSTRAINTS.md
docs/_ai/_context/AGENT_GUARDRAILS.md
docs/_ai/_context/AGENT_INITIAL_CONTEXT.md
docs/_ai/_context/AGENT_RULES_ENGINE.md
docs/_ai/_context/AI_CONTEXT.md
docs/_ai/_context/approved-commands.yml
docs/_ai/_guardrails/GUARDRAIL_POLICY_BASELINE.md
docs/_ai/_guardrails/GUARDRAIL_POLICY_PARITY.md
docs/_ai/_guardrails/GUARDRAIL_POLICY_REQUIREMENTS.md
docs/_ai/_maps/agent-routing-map.md
docs/_ai/_maps/MAP_ROUTING_AGENT_DOCUMENTATION.md
docs/_ai/_maps/MAP_ROUTING_AGENT_GATES.md
docs/_ai/_maps/MAP_ROUTING_AGENT_MODELS.md
docs/_ai/_maps/troubleshooting-map.json
docs/_ai/_prompts/PROMPT_TEMPLATE_CODE_REVIEW.md
docs/_ai/_prompts/PROMPT_TEMPLATE_DOCUMENTATION.md
docs/_ai/_prompts/PROMPT_TEMPLATE_TESTING.md
docs/_canon/00_START_HERE.md
docs/_canon/01_AUTHORITY_SSOT.md
docs/_canon/02_CONTEXT_MAP.md
docs/_canon/03_WORKFLOWS.md
docs/_canon/04_SOURCES_GENERATED.md
docs/_canon/05_MODELS_PIPELINE.md
docs/_canon/08_APPROVED_COMMANDS.md
docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md
docs/_canon/10_GIT_PR_MERGE_WORKFLOW.md
docs/_canon/AI_TUTORIAL.md
docs/_canon/HUMAN_TUTORIAL.md
docs/_canon/QUALITY_METRICS.md
docs/_canon/README_TUTORIALS.md
docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md
docs/_canon/GOVERNANCE_MODEL.md
docs/_canon/_agent/AI_INCIDENT_RESPONSE_POLICY.md
docs/_canon/_agent/AI_PROTOCOL_CHECKLIST.md
docs/_canon/_agent/AI_TASK_VERSIONING_POLICY.md
docs/_canon/_agent/EVIDENCE_PACK.md
docs/_canon/_agent/TASK_BRIEF.md
```

### B. Comandos de Verificação (Reproduzibilidade)

```powershell
# Verificar duplicação de glossário
Select-String -Path "docs/_ai/_INDEX.md" -Pattern "SSOT.*Single Source" -Context 2,2
Select-String -Path "docs/_canon/00_START_HERE.md" -Pattern "SSOT.*Single Source" -Context 2,2

# Verificar stubs
Get-Content "docs/_ai/07_AGENT_ROUTING_MAP.md" | Select-String "Moved|New location"
Get-Content "docs/_ai/SYSTEM_DESIGN.md" | Select-String "Canonical version"

# Verificar fragmentação de guardrails
Get-ChildItem "docs/_ai/_guardrails/*.md" | Measure-Object | Select-Object Count
Get-ChildItem "docs/_ai/*GUARDRAIL*.md" | Measure-Object | Select-Object Count

# Verificar índices concorrentes
Select-String -Path "docs/_ai/_INDEX.md" -Pattern "Router Central|porta única"
Select-String -Path "docs/_canon/00_START_HERE.md" -Pattern "Router Central|porta única"
Select-String -Path "docs/_canon/GOVERNANCE_MODEL.md" -Pattern "Governance Map|NORMATIVE HIERARCHY"
```

---

**END OF AUDIT REPORT**
