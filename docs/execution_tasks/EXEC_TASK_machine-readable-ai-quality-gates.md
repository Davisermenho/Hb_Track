# EXEC_TASK — Machine-Readable Documentation & AI Quality Gates (ADR-016)

**Status:** PENDENTE
**Prioridade:** P0 (Fase 1) → P1 (Fase 2) → P2 (Fases 3–4)
**Assignee:** Agente IA + Dev
**Escopo:** Cross-module (monorepo `C:\HB TRACK`)
**ADR Fonte:** [`016-ADR-machine-readable-ai-quality-gates.md`](../ADR/016-ADR-machine-readable-ai-quality-gates.md)
**ADR Complementar:** [`017-ADR-DOCS-documentacao-humana.md`](../ADR/017-ADR-DOCS-documentacao-humana.md)
**Data:** 2026-02-11

---

## Inventário do Estado Atual (Audit de Placeholders)

> Antes de implementar, é obrigatório saber o que existe e o que é placeholder.
> Esta secção documenta o estado de cada artefato referenciado pela ADR-016.

### Estrutura `docs/_ai/` (criada, com placeholders)

| Path | Estado | Conteúdo Real? |
|------|--------|----------------|
| `docs/_ai/_INDEX.md` | Existente | Sim — router funcional |
| `docs/_ai/_context/AGENT_INITIAL_CONTEXT.md` | Placeholder | Verificar |
| `docs/_ai/_context/AGENT_CONSTRAINTS.md` | Placeholder | Verificar |
| `docs/_ai/_context/AGENT_GUARDRAILS.md` | Placeholder | Verificar |
| `docs/_ai/_context/AGENT_RULES_ENGINE.md` | Placeholder | Verificar |
| `docs/_ai/_specs/SPEC_AGENT_GATES.yaml` | Placeholder | TODO section, estrutura parcial |
| `docs/_ai/_specs/SPEC_AGENT_ROUTING.json` | Placeholder | Verificar |
| `docs/_ai/_specs/SPEC_AGENT_MODELS.json` | Placeholder | Verificar |
| `docs/_ai/_schemas/agent-spec.schema.json` | Placeholder | Verificar |
| `docs/_ai/_schemas/quality-gates.schema.json` | Existente | Parcial — schema draft-07, faltam campos |
| `docs/_ai/_schemas/invocation.schema.json` | Placeholder | Verificar |
| `docs/_ai/_prompts/PROMPT_TEMPLATE_*.md` (3) | Placeholder | Verificar |
| `docs/_ai/_maps/MAP_ROUTING_AGENT_*.md` (3) | Placeholder | Verificar |
| `docs/_ai/_guardrails/GUARDRAIL_POLICY_*.md` (3) | Placeholder | Verificar |
| `docs/_ai/_checklists/CHECKLIST_AGENT_*.md` (3) | Placeholder | Verificar |
| `docs/_ai/_docs_arch/DOCS_ARCH_MASTER.md` | Placeholder | Verificar |
| `docs/_ai/.aiignore` | Existente | Verificar conteúdo |

### Estrutura `docs/scripts/_ia/` (criada, com placeholders)

| Path | Estado | Conteúdo Real? |
|------|--------|----------------|
| `docs/scripts/_ia/README.md` | Existente | Documentação de interface (correcta) |
| `docs/scripts/_ia/requirements.txt` | Existente | Verificar dependências |
| `docs/scripts/_ia/extractors/extract-quality-gates.py` | Placeholder | `TODO: implement` (pass) |
| `docs/scripts/_ia/extractors/extract-ai-context.py` | Placeholder | Verificar |
| `docs/scripts/_ia/extractors/extract-workflows.py` | Placeholder | Verificar |
| `docs/scripts/_ia/extractors/extract-adr-index.py` | Placeholder | Verificar |
| `docs/scripts/_ia/extractors/extract-approved-commands.py` | Placeholder | Verificar |
| `docs/scripts/_ia/extractors/extract-troubleshooting.py` | Placeholder | Verificar |
| `docs/scripts/_ia/validators/validate-ai-docs-sync.py` | Placeholder | Verificar |
| `docs/scripts/_ia/validators/validate-quality-gates.py` | Placeholder | Verificar |
| `docs/scripts/_ia/validators/validate-agent-spec.py` | Placeholder | Verificar |
| `docs/scripts/_ia/validators/validate-approved-commands.py` | Placeholder | Verificar |
| `docs/scripts/_ia/validators/validate-yaml-json.py` | Placeholder | Verificar |
| `docs/scripts/_ia/generators/generate-*.py` (4) | Placeholder | Verificar |
| `docs/scripts/_ia/agents/*.py` (3) | Placeholder | Verificar |
| `docs/scripts/_ia/utils/*.py` (4) | Placeholder | Verificar |

### GitHub Workflows (criados, com TODO)

| Path | Estado | Conteúdo Real? |
|------|--------|----------------|
| `.github/workflows/quality-gates.yml` | Placeholder | `TODO - Check quality gates` (step inativo) |
| `.github/workflows/ai-docs-validation.yml` | Placeholder | `TODO - Validate AI docs sync` (step inativo) |
| `.github/workflows/approved-commands-check.yml` | Placeholder | Verificar |
| `.github/workflows/agent-spec-validation.yml` | Placeholder | Verificar |
| `.github/workflows/generate-ai-artifacts.yml` | Placeholder | Verificar |

### Ficheiros raiz

| Path | Estado | Conteúdo Real? |
|------|--------|----------------|
| `.aiprompt` | Verificar existência | — |
| `.github/.copilotignore` | Verificar existência | — |

---

## Fase 0: Audit e Preparação (P0 — Pré-requisito)

### Objectivo
Auditar todos os placeholders, classificá-los como REAL/PLACEHOLDER/AUSENTE, e produzir uma worklist verificável.

### 0.1 Leitura obrigatória (ordem)

1. [`docs/_canon/00_START_HERE.md`](../docs/_canon/00_START_HERE.md) — Router central
2. [`docs/_canon/01_AUTHORITY_SSOT.md`](../docs/_canon/01_AUTHORITY_SSOT.md) — Precedência
3. [`docs/_canon/QUALITY_METRICS.md`](../docs/_canon/QUALITY_METRICS.md) — Fonte SSOT de métricas
4. [`docs/ADR/016-ADR-machine-readable-ai-quality-gates.md`](../ADR/016-ADR-machine-readable-ai-quality-gates.md) — Decisão
5. [`docs/ADR/017-ADR-DOCS-documentacao-humana.md`](../ADR/017-ADR-DOCS-documentacao-humana.md) — Complemento

### 0.2 Tarefas de Audit

- [ ] **AUDIT-01**: Para cada ficheiro listado no inventário acima, abrir e classificar:
  - `REAL` = conteúdo funcional implementado
  - `PLACEHOLDER` = contém `TODO`, `pass`, ou estrutura vazia
  - `AUSENTE` = ficheiro não existe
- [ ] **AUDIT-02**: Registar resultado no inventário (actualizar esta secção)
- [ ] **AUDIT-03**: Verificar existência de `.aiprompt` e `.github/.copilotignore` na raiz
- [ ] **AUDIT-04**: Verificar conteúdo de `docs/scripts/_ia/requirements.txt` (dependências: radon, lizard, pyyaml, jsonschema)

### 0.3 Critério de passagem

O Audit está COMPLETO quando:
- [ ] Todos os ficheiros classificados (nenhum "Verificar" restante)
- [ ] Worklist de Fase 1 gerada com lista exacta de ficheiros a implementar

---

## Fase 1: Implementação dos Extractors e Specs (P0 — Sprint actual)

### Objectivo
Transformar a documentação canônica humana (`docs/_canon/`) em artefatos machine-readable (`docs/_ai/_specs/`) com extractors reais (não placeholders).

### 1.1 Pré-condições

```powershell
# Verificações obrigatórias (ABORT se falhar)
Set-Location "C:\HB TRACK"
Test-Path .\docs\_canon\QUALITY_METRICS.md          # True
Test-Path .\docs\_canon\03_WORKFLOWS.md              # True
Test-Path .\docs\_canon\08_APPROVED_COMMANDS.md      # True
Test-Path .\scripts\_ia\requirements.txt             # True
python --version                                      # >= 3.11
pip install -r docs/scripts/_ia/requirements.txt           # exit 0
```

### 1.2 Extractor: quality-gates (P0 — Prioridade máxima)

**Ficheiro:** `docs/scripts/_ia/extractors/extract-quality-gates.py`
**Entrada SSOT:** `docs/_canon/QUALITY_METRICS.md`
**Saída:** `docs/_ai/_specs/quality-gates.yml`

**Requisitos obrigatórios:**
- [ ] Ler `QUALITY_METRICS.md` e extrair todos os thresholds (complexidade ciclomática, LOC max, cobertura mínima, etc.)
- [ ] Gerar YAML válido contra `docs/_ai/_schemas/quality-gates.schema.json`
- [ ] Incluir metadados: `version`, `source_file`, `generated_at` (ISO 8601)
- [ ] Exit code: 0 = sucesso, 1 = erro de parsing, 2 = schema inválido
- [ ] **Anti-falso-positivo**: Se `QUALITY_METRICS.md` não contiver threshold esperado, ABORT com mensagem (não inventar default)

**Teste de validação (obrigatório):**
```powershell
Set-Location "C:\HB TRACK"
python scripts\_ia\extractors\extract-quality-gates.py --output docs\_ai\_specs\quality-gates.yml
$LASTEXITCODE  # Esperado: 0

# Validar YAML gerado contra schema
python scripts\_ia\validators\validate-yaml-json.py --file docs\_ai\_specs\quality-gates.yml --schema docs\_ai\_schemas\quality-gates.schema.json
$LASTEXITCODE  # Esperado: 0

# Anti-falso-positivo: se esvaziar QUALITY_METRICS.md temporariamente
# deve falhar com exit 1 (não gerar YAML com defaults inventados)
```

### 1.3 Extractor: ai-context (P0)

**Ficheiro:** `docs/scripts/_ia/extractors/extract-ai-context.py`
**Entrada SSOT:** `docs/_canon/00_START_HERE.md` + `docs/_canon/01_AUTHORITY_SSOT.md`
**Saída:** `docs/_ai/_context/AI_CONTEXT.md`

**Requisitos obrigatórios:**
- [ ] Gerar ficheiro compacto (< 100 linhas) com: ROLE_TOKEN, regras top-5, referências a docs canônicos
- [ ] Formato: Markdown com frontmatter YAML (`version`, `source_files`, `generated_at`)
- [ ] Exit code: 0 = sucesso, 1 = erro

### 1.4 Extractor: approved-commands (P0)

**Ficheiro:** `docs/scripts/_ia/extractors/extract-approved-commands.py`
**Entrada SSOT:** `docs/_canon/08_APPROVED_COMMANDS.md`
**Saída:** `docs/_ai/_specs/approved-commands.yml`

**Requisitos obrigatórios:**
- [ ] Extrair whitelist de comandos + categoria (allowed/prohibited/conditional)
- [ ] YAML válido, parseable por CI
- [ ] Exit code: 0 = sucesso, 1 = erro

### 1.5 Completar Schema: quality-gates.schema.json (P0)

**Ficheiro:** `docs/_ai/_schemas/quality-gates.schema.json`

**Estado actual:** Schema parcial (só `loc_max`, `complexity_max`, `coverage_min`).

**Requisitos:**
- [ ] Adicionar campos faltantes: `maintainability_index_min`, `halstead_volume_max`, `function_length_max`, `allowed_profiles` (conforme `QUALITY_METRICS.md`)
- [ ] Adicionar `required` fields
- [ ] Adicionar `additionalProperties: false` para prevenir drift
- [ ] Adicionar metadados: `source_file`, `generated_at`

### 1.6 Completar agent-spec.schema.json (P0)

**Ficheiro:** `docs/_ai/_schemas/agent-spec.schema.json`

**Requisitos:**
- [ ] Definir schema para: `role_token`, `ack_protocol`, `ask_protocol`, `invocation_protocol`
- [ ] Validar contra draft-07 ou draft-2020-12
- [ ] Testar com `validate-yaml-json.py`

### 1.7 Ficheiros raiz (P0)

- [ ] Criar/verificar `.aiprompt` na raiz do repo apontando para `docs/_ai/_INDEX.md`
- [ ] Criar/verificar `.github/.copilotignore` com paths de exclusão (`__pycache__`, `_scratch/`, `.env`, `secrets/`)

---

## Fase 2: Validators e CI Workflows (P1 — Próxima sprint)

### Objectivo
Implementar validação automática em CI que bloqueia PRs com drift SSOT ↔ AI ou violação de quality gates.

### 2.1 Validator: validate-quality-gates.py (P1)

**Ficheiro:** `docs/scripts/_ia/validators/validate-quality-gates.py`

**Requisitos obrigatórios:**
- [ ] Ler thresholds de `docs/_ai/_specs/quality-gates.yml`
- [ ] Usar `radon` para complexidade ciclomática dos ficheiros Python alterados no PR
- [ ] Usar `lizard` para LOC/function length (opcional, confirmar com `QUALITY_METRICS.md`)
- [ ] Saída: JSON com `{file, metric, value, threshold, status: pass|fail}`
- [ ] Exit code: 0 = tudo pass, 1 = crash, 4 = violação (alinhado com `exit_codes.md`)

**Teste de validação:**
```powershell
# Teste positivo: ficheiro conformante
python scripts\_ia\validators\validate-quality-gates.py --file "Hb Track - Backend\app\models\training_session.py"
$LASTEXITCODE  # Esperado: 0

# Anti-falso-positivo: criar ficheiro com complexidade alta (nested ifs)
# Deve retornar exit 4 com detalhe do threshold violado
```

### 2.2 Validator: validate-ai-docs-sync.py (P1)

**Ficheiro:** `docs/scripts/_ia/validators/validate-ai-docs-sync.py`

**Requisitos obrigatórios:**
- [ ] Comparar timestamps: se doc SSOT (`docs/_canon/`) é mais recente que doc AI derivado (`docs/_ai/`), emitir warning
- [ ] Comparar hashes: se conteúdo SSOT mudou desde última geração, emitir fail
- [ ] Mapeamento SSOT → AI definido em config (YAML ou hardcoded inicialmente):
  - `QUALITY_METRICS.md` → `quality-gates.yml`
  - `08_APPROVED_COMMANDS.md` → `approved-commands.yml`
  - `03_WORKFLOWS.md` → `workflows.yml`
- [ ] Exit code: 0 = sync, 1 = crash, 3 = out-of-sync

**Teste de validação:**
```powershell
# Depois de gerar extractors, deve estar sincronizado
python scripts\_ia\validators\validate-ai-docs-sync.py --strict
$LASTEXITCODE  # Esperado: 0

# Anti-falso-positivo: editar QUALITY_METRICS.md sem regenerar quality-gates.yml
# Deve retornar exit 3
```

### 2.3 Validator: validate-agent-spec.py (P1)

**Ficheiro:** `docs/scripts/_ia/validators/validate-agent-spec.py`

**Requisitos:**
- [ ] Validar `docs/_ai/_specs/agent-spec.json` contra `docs/_ai/_schemas/agent-spec.schema.json`
- [ ] Exit code: 0 = válido, 2 = schema violation

### 2.4 Validator: validate-approved-commands.py (P1)

**Ficheiro:** `docs/scripts/_ia/validators/validate-approved-commands.py`

**Requisitos:**
- [ ] Ler `approved-commands.yml`
- [ ] Varrer scripts em `scripts/` e `.github/workflows/` por comandos não listados na whitelist
- [ ] Exit code: 0 = todos aprovados, 4 = comando não autorizado detectado

### 2.5 Workflows GitHub Actions (P1)

#### 2.5.1 quality-gates.yml (já existe como placeholder)

**Ficheiro:** `.github/workflows/quality-gates.yml`

**Requisitos:**
- [ ] Substituir step `TODO` por execução real de `validate-quality-gates.py`
- [ ] Trigger em `pull_request` (paths: `Hb Track - Backend/**`, `scripts/**`)
- [ ] Step: instalar deps → executar validator → falhar PR se exit ≠ 0

#### 2.5.2 ai-docs-validation.yml (já existe como placeholder)

**Ficheiro:** `.github/workflows/ai-docs-validation.yml`

**Requisitos:**
- [ ] Substituir step `TODO` por execução real de `validate-ai-docs-sync.py`
- [ ] Trigger em `push` e `pull_request` (paths: `docs/_canon/**`, `docs/_ai/**`)

#### 2.5.3 approved-commands-check.yml

**Ficheiro:** `.github/workflows/approved-commands-check.yml`

**Requisitos:**
- [ ] Activar com `validate-approved-commands.py`
- [ ] Trigger em `pull_request` (paths: `scripts/**`, `.github/workflows/**`)

---

## Fase 3: Checklists, Workflows e Generators (P2 — Backlog)

### Objectivo
Completar o ecossistema com workflows machine-readable, checklists executáveis e generators automáticos.

### 3.1 Extractor: workflows (P2)

**Ficheiro:** `docs/scripts/_ia/extractors/extract-workflows.py`
**Entrada SSOT:** `docs/_canon/03_WORKFLOWS.md`
**Saída:** `docs/_ai/_specs/workflows.yml`

### 3.2 Generator: adr-index (P2)

**Ficheiro:** `docs/scripts/_ia/generators/generate-ai-index.py`
**Saída:** `docs/_ai/_maps/adr-index.json`

### 3.3 Generator: checklists (P2)

**Ficheiro:** `docs/scripts/_ia/generators/generate-checklist-yml.py`
**Saída:** `docs/_ai/_checklists/checklist-models.yml`

### 3.4 Completar guardrails (P2)

**Ficheiro:** `docs/_ai/_guardrails/security-policy.yml` (NOVO)

**Requisitos:**
- [ ] Definir lista de prohibitions (`eval`, `exec`, `log.*password`, `log.*cpf`)
- [ ] Severity: `blocker` vs `warning`
- [ ] CI step que varre código contra prohibitions

---

## Fase 4: Integração com Agentes (P2 — Backlog)

### Objectivo
Garantir que agentes (Copilot, Cursor, Cline, Claude) consomem os artefatos machine-readable correctamente.

### 4.1 Agent handshake protocol (P2)

**Requisitos:**
- [ ] `agent-spec.json` define ACK obrigatório: agente cita `ROLE_TOKEN` + top-3 regras antes de agir
- [ ] Sem ACK correcto, agente não prossegue
- [ ] Testar com Copilot Chat: "resuma o contexto do projeto" → deve citar `AI_CONTEXT.md`

### 4.2 Testar em PRs reais (P2)

- [ ] Submeter PR com código que viola complexidade → CI bloqueia
- [ ] Submeter PR que edita `QUALITY_METRICS.md` sem regenerar `quality-gates.yml` → CI bloqueia
- [ ] Submeter PR com comando não aprovado em script → CI alerta

### 4.3 Agent code-review (P2)

**Ficheiro:** `docs/scripts/_ia/agents/code-review-agent.py`

**Requisitos:**
- [ ] Ler `quality-gates.yml` + `security-policy.yml`
- [ ] Analisar ficheiros alterados no PR
- [ ] Emitir relatório: `{file, issues: [{rule, severity, line, message}]}`

---

## Checklist Canônica de Implementação

> Usar como tracking global. Marcar `[x]` apenas quando o critério de aceite associado estiver validado.

### Fase 0 — Audit
- [ ] AUDIT-01: Todos os ficheiros classificados (REAL/PLACEHOLDER/AUSENTE)
- [ ] AUDIT-02: Inventário actualizado neste documento
- [ ] AUDIT-03: `.aiprompt` e `.copilotignore` verificados
- [ ] AUDIT-04: `requirements.txt` validado

### Fase 1 — Extractors e Specs
- [ ] `extract-quality-gates.py` implementado e testado (exit 0 + YAML válido)
- [ ] `extract-ai-context.py` implementado e testado
- [ ] `extract-approved-commands.py` implementado e testado
- [ ] `quality-gates.schema.json` completo (todos os campos de QUALITY_METRICS)
- [ ] `agent-spec.schema.json` completo (ACK/ASK/INVOCATION)
- [ ] `.aiprompt` aponta para `docs/_ai/_INDEX.md`
- [ ] `.github/.copilotignore` configurado

### Fase 2 — Validators e CI
- [ ] `validate-quality-gates.py` implementado (radon + lizard)
- [ ] `validate-ai-docs-sync.py` implementado (hash comparison)
- [ ] `validate-agent-spec.py` implementado (schema validation)
- [ ] `validate-approved-commands.py` implementado (whitelist scan)
- [ ] `quality-gates.yml` workflow activado (não-TODO)
- [ ] `ai-docs-validation.yml` workflow activado (não-TODO)
- [ ] `approved-commands-check.yml` workflow activado

### Fase 3 — Generators e Checklists
- [ ] `extract-workflows.py` implementado
- [ ] `generate-ai-index.py` implementado
- [ ] `generate-checklist-yml.py` implementado
- [ ] `security-policy.yml` criado com prohibitions

### Fase 4 — Integração com Agentes
- [ ] `agent-spec.json` com ACK protocol funcional
- [ ] PR com violação de qualidade → bloqueado por CI
- [ ] PR com drift SSOT ↔ AI → bloqueado por CI
- [ ] `code-review-agent.py` funcional localmente

---

## Critérios de Aceite (Definition of Done — DoD)

### DoD-0: Princípio de Não-Invenção
> Nenhum threshold, constraint, ou regra pode ser inventado. Tudo deve ser extraído de uma fonte SSOT canônica existente.

**Validação:** Comparar cada valor em `quality-gates.yml` com o valor original em `QUALITY_METRICS.md`. Diferenças = FAIL.

### DoD-1: Schema Validation
> Todo artefato YAML/JSON gerado deve passar validação contra seu JSON Schema correspondente.

**Validação:**
```powershell
python scripts\_ia\validators\validate-yaml-json.py --file <artefato> --schema <schema>
# Exit 0 = PASS
```

### DoD-2: Extractor Idempotency
> Rodar um extractor N vezes consecutivas deve produzir output idêntico (excepto `generated_at`).

**Validação:**
```powershell
python scripts\_ia\extractors\extract-quality-gates.py --output /tmp/run1.yml
python scripts\_ia\extractors\extract-quality-gates.py --output /tmp/run2.yml
# Diff (ignorando generated_at) deve ser vazio
```

### DoD-3: Anti-Falso-Positivo (Extractors)
> Se a fonte SSOT não contiver dados esperados, o extractor deve ABORT (exit 1), não gerar valores default.

**Validação:**
```powershell
# Esvaziar temporariamente QUALITY_METRICS.md
# Rodar extractor
# Esperado: exit 1, mensagem descritiva, sem YAML gerado
```

### DoD-4: Anti-Falso-Positivo (Validators)
> Se código está conforme, validator deve retornar exit 0. Se viola, deve retornar exit 4 com detalhe.

**Validação:**
```powershell
# Ficheiro conformante → exit 0
# Ficheiro com complexidade 15 (threshold 6) → exit 4, output mostra {file, metric: "cyclomatic_complexity", value: 15, threshold: 6}
```

### DoD-5: Sync Detection
> Alteração em doc SSOT sem regenerar doc AI derivado deve ser detectada pelo validator de sync.

**Validação:**
```powershell
# Editar QUALITY_METRICS.md (mudar threshold)
# Sem regenerar quality-gates.yml
python scripts\_ia\validators\validate-ai-docs-sync.py --strict
# Esperado: exit 3 + mensagem: "QUALITY_METRICS.md modified since last generation"
```

### DoD-6: CI Enforcement
> PRs que violem quality gates ou sync devem ser bloqueados por GitHub Actions.

**Validação:**
- Submeter PR com ficheiro Python com complexidade > threshold → status check FAIL
- Submeter PR com doc SSOT editado sem regenerar AI → status check FAIL

### DoD-7: Exit Code Alignment
> Todos os scripts seguem a convenção de exit codes do projecto (`docs/references/exit_codes.md`):
- 0 = pass
- 1 = crash / parsing error
- 2 = parity / schema warning
- 3 = sync mismatch / guard violation
- 4 = requirements / quality violation

**Validação:** Para cada script, testar pelo menos 2 cenários (pass + fail) e verificar exit codes.

### DoD-8: Portabilidade de Path
> Scripts devem funcionar tanto com paths Windows (`\`) como POSIX (`/`). Usar `pathlib.Path` ou `os.path.join`.

**Validação:** Testar em Windows (PowerShell) e verificar que paths não estão hardcoded.

### DoD-9: Documentação Actualizada
> Ao completar cada fase, actualizar:
- Este EXEC_TASK (marcar items como `[x]`)
- `docs/_ai/_INDEX.md` (se novos ficheiros AI foram criados)
- `docs/_canon/00_START_HERE.md` (se novos artefatos de governança foram adicionados)

---

## Testes de Validação (Sem Falso Positivo)

### Teste 1: Extractor Quality Gates — Happy Path
```powershell
Set-Location "C:\HB TRACK"
python scripts\_ia\extractors\extract-quality-gates.py --output docs\_ai\_specs\quality-gates.yml
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 0
# 2. Test-Path docs\_ai\_specs\quality-gates.yml -eq True
# 3. Conteúdo YAML contém "complexity_max" com valor igual ao de QUALITY_METRICS.md
# 4. Conteúdo YAML contém "version" e "generated_at"
```

### Teste 2: Extractor Quality Gates — Fonte Vazia (Anti-Falso-Positivo)
```powershell
Set-Location "C:\HB TRACK"
# Backup
Copy-Item docs\_canon\QUALITY_METRICS.md docs\_canon\QUALITY_METRICS.md.bak
# Esvaziar fonte
Set-Content docs\_canon\QUALITY_METRICS.md "# empty"
python scripts\_ia\extractors\extract-quality-gates.py --output /tmp/should_not_exist.yml
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 1 (ABORT, não 0)
# 2. Output contém mensagem de erro descritiva
# 3. /tmp/should_not_exist.yml NÃO foi criado

# Restore
Move-Item docs\_canon\QUALITY_METRICS.md.bak docs\_canon\QUALITY_METRICS.md -Force
```

### Teste 3: Schema Validation — YAML Válido
```powershell
python scripts\_ia\validators\validate-yaml-json.py `
  --file docs\_ai\_specs\quality-gates.yml `
  --schema docs\_ai\_schemas\quality-gates.schema.json
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 0
```

### Teste 4: Schema Validation — YAML Inválido (Anti-Falso-Positivo)
```powershell
# Criar YAML propositadamente inválido
Set-Content $env:TEMP\bad-gates.yml "version: 'not-semver'`ngates:`n  complexity_max: 'not-a-number'"
python scripts\_ia\validators\validate-yaml-json.py `
  --file $env:TEMP\bad-gates.yml `
  --schema docs\_ai\_schemas\quality-gates.schema.json
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 2 (schema violation)
# 2. Output indica campo(s) inválido(s)
```

### Teste 5: Sync Validator — Sincronizado
```powershell
# Após gerar todos os extractors:
python scripts\_ia\validators\validate-ai-docs-sync.py --strict
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 0
```

### Teste 6: Sync Validator — Dessincronizado (Anti-Falso-Positivo)
```powershell
# Editar QUALITY_METRICS.md (mudar um threshold)
Add-Content docs\_canon\QUALITY_METRICS.md "`n<!-- drift_test -->"
python scripts\_ia\validators\validate-ai-docs-sync.py --strict
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 3 (out-of-sync)
# 2. Output indica qual par SSOT↔AI está dessincronizado

# Restore
git restore -- docs\_canon\QUALITY_METRICS.md
```

### Teste 7: Quality Gates Validator — Código Conformante
```powershell
# Escolher ficheiro Python simples (baixa complexidade)
python scripts\_ia\validators\validate-quality-gates.py `
  --file "Hb Track - Backend\app\models\__init__.py"
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 0
# 2. Output JSON: todos os metrics com status "pass"
```

### Teste 8: Quality Gates Validator — Código Violador (Anti-Falso-Positivo)
```powershell
# Criar ficheiro temporário com complexidade alta
$tempFile = "$env:TEMP\high_complexity.py"
@"
def complex_function(a, b, c, d, e, f, g):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                return True
    return False
"@ | Set-Content $tempFile

python scripts\_ia\validators\validate-quality-gates.py --file $tempFile
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 4 (quality violation)
# 2. Output JSON: metric "cyclomatic_complexity" com status "fail", value > threshold

Remove-Item $tempFile
```

### Teste 9: Approved Commands — Comando Aprovado
```powershell
python scripts\_ia\validators\validate-approved-commands.py `
  --scan-dir scripts\
$ec = $LASTEXITCODE

# Assertions
# 1. $ec -eq 0 (todos os comandos em scripts/ estão na whitelist)
```

### Teste 10: Idempotency — Extractor Determinístico
```powershell
python scripts\_ia\extractors\extract-quality-gates.py --output $env:TEMP\run1.yml
python scripts\_ia\extractors\extract-quality-gates.py --output $env:TEMP\run2.yml

# Comparar (ignorando generated_at)
$r1 = (Get-Content $env:TEMP\run1.yml) -replace 'generated_at:.*', ''
$r2 = (Get-Content $env:TEMP\run2.yml) -replace 'generated_at:.*', ''

# Assertions
# 1. $r1 -eq $r2 (conteúdo idêntico excepto timestamp)
```

---

## Relatório de Cobertura (Template)

> Preencher ao concluir cada fase.

### Fase 1

| Artefato | Estado | Ficheiro de teste | Evidência | DoD |
|----------|--------|-------------------|-----------|-----|
| `extract-quality-gates.py` | PENDENTE | Testes 1, 2, 10 | — | DoD-0, DoD-2, DoD-3 |
| `extract-ai-context.py` | PENDENTE | — | — | DoD-0, DoD-2 |
| `extract-approved-commands.py` | PENDENTE | — | — | DoD-0, DoD-2 |
| `quality-gates.schema.json` | PENDENTE | Testes 3, 4 | — | DoD-1 |
| `agent-spec.schema.json` | PENDENTE | — | — | DoD-1 |
| `.aiprompt` | PENDENTE | — | — | DoD-9 |
| `.copilotignore` | PENDENTE | — | — | DoD-9 |

### Fase 2

| Artefato | Estado | Ficheiro de teste | Evidência | DoD |
|----------|--------|-------------------|-----------|-----|
| `validate-quality-gates.py` | PENDENTE | Testes 7, 8 | — | DoD-4, DoD-7 |
| `validate-ai-docs-sync.py` | PENDENTE | Testes 5, 6 | — | DoD-5, DoD-7 |
| `validate-agent-spec.py` | PENDENTE | — | — | DoD-1, DoD-7 |
| `validate-approved-commands.py` | PENDENTE | Teste 9 | — | DoD-4, DoD-7 |
| `quality-gates.yml` (workflow) | PENDENTE | — | — | DoD-6 |
| `ai-docs-validation.yml` (workflow) | PENDENTE | — | — | DoD-6 |

---

## Regras de Parada (Anti-Alucinação)

1. **Não inventar thresholds**: Se `QUALITY_METRICS.md` não define um valor, não usar default. Marcar PENDING.
2. **Não inventar schemas**: Se não há spec para um campo, não adicionar ao JSON Schema. Marcar PENDING.
3. **Não implementar fora do escopo**: Apenas criar/actualizar ficheiros listados neste EXEC_TASK.
4. **Não editar artefatos gerados**: `docs/_generated/*` é READ-ONLY.
5. **Não executar refactors**: Se um extractor/validator precisa de mudança em doc canônico, marcar PENDING e pedir actualização do SSOT.
6. **Exit codes canônicos**: Sempre usar 0/1/2/3/4 conforme `exit_codes.md`. Nunca inventar novos.

---

## Dependências entre ADRs

```
ADR-001 (SSOT Precedência)
    │
    ├── ADR-008 (Governança por Artefatos)
    │       │
    │       ├── ADR-016 (Machine-Readable / AI Quality Gates) ← ESTA EXEC_TASK
    │       │       │
    │       │       └── ADR-017 (Documentação Humana) — complemento
    │       │
    │       └── ADR-004 (Invariantes como Contrato)
    │
    └── ADR-002 (TRD por Referência)
```

---

## Notas Finais

- **Prioridade real**: Fase 1 (extractors) é o foundation. Sem extractors reais, validators não têm input. Sem validators, CI não bloqueia. Sem CI, quality gates são sugestão, não enforcement.
- **Incremental**: Cada extractor/validator é independente. Implementar um de cada vez, testar, commitar.
- **Este EXEC_TASK é um documento vivo**: Actualizar estado à medida que fases são completadas.
- **Precedência**: Em conflito, `docs/_canon/` vence `docs/_ai/` vence este EXEC_TASK.
