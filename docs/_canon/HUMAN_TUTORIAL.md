# Tutorial: Fluxo de Desenvolvimento Humano com Artefatos AI

**Versão:** 3.0  
**Data:** 2026-02-12  
**Público:** Desenvolvedores humanos trabalhando com HB Track  
**Baseado em:** IMPLEMENTATION_SUMMARY.md

---

## 1. Pré-requisitos

### Dependências Obrigatórias
- **PowerShell 5.1+** (Windows) ou PowerShell Core 7+
- **Python 3.9+** com venv configurado
- **Git 2.30+**
- **Docker** e **Docker Compose** (para PostgreSQL local)
- **PyYAML 6.0.1+** (citar `docs/scripts/_ia/requirements.txt`)
- **Radon** (para análise de complexidade ciclomática)

### Setup do Ambiente Python

```powershell
# Entre no diretório backend
cd "Hb Track - Backend"

# Crie e ative o ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instale dependências do projeto
pip install -r requirements.txt

# Instale dependências dos scripts AI
pip install -r ..\scripts\_ia\requirements.txt
```

**Evidência:** `docs/scripts/_ia/utils/yaml_loader.py` (linha 17) requer PyYAML 6.0.1+

### Validação de CWD (Current Working Directory)

**IMPORTANTE:** Scripts diferentes exigem CWDs diferentes:

| Comando | CWD Esperado |
|---------|-------------|
| Scripts em `scripts\_ia\` | **Repo root** (`C:\HB TRACK`) |
| Scripts backend (models_autogen_gate.ps1, etc) | **Backend root** (`C:\HB TRACK\Hb Track - Backend`) |

**Validação obrigatória:**

```powershell
# Para scripts AI (repo root)
if (-not (Test-Path "scripts\_ia")) {
    Write-Host "[ERROR] Wrong CWD. Expected: repo root" -ForegroundColor Red
    exit 1
}

# Para scripts backend
$expectedPath = "Hb Track - Backend"
$currentPath = Get-Location
if ($currentPath -notmatch [regex]::Escape($expectedPath)) {
    Write-Host "[ERROR] Wrong CWD. Expected: *\$expectedPath" -ForegroundColor Red
    exit 1
}
```

---

## 2. Comandos Canônicos (PowerShell)

### 2.1 Extratores

#### extract-approved-commands.py

**Propósito:** Converte `docs\_canon\08_APPROVED_COMMANDS.md` → `docs\_ai\_context\approved-commands.yml` (whitelist de comandos para validação de scripts)

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\extractors\extract-approved-commands.py
```

**Saída:** `docs\_ai\_context\approved-commands.yml`

**Verificação:**
```powershell
Get-Content docs\_ai\_context\approved-commands.yml | Select-String "version"
# Esperado: version: '1.0'
```

**Exit codes:**
- **0:** Extração bem-sucedida
- **1:** Arquivo fonte não encontrado

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 46-54), `docs/scripts/_ia/extractors/extract-approved-commands.py`

---

#### extract-troubleshooting.py

**Propósito:** Converte `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md` → `docs\_ai\_maps\troubleshooting-map.json` (mapa de diagnóstico por exit code)

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\extractors\extract-troubleshooting.py
```

**Saída:** `docs\_ai\_maps\troubleshooting-map.json`

**Verificação:**
```powershell
python scripts\_ia\utils\json_loader.py
# Smoke test para validar JSON
```

**Exit codes:**
- **0:** Extração bem-sucedida (4 exit codes mapeados)
- **1:** Arquivo fonte não encontrado

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 56-65), `docs/scripts/_ia/extractors/extract-troubleshooting.py`

---

### 2.2 Geradores

#### generate-handshake-template.py

**Propósito:** Gera template de protocolo ACK/ASK/EXECUTE para agents

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\generators\generate-handshake-template.py
```

**Saída:** `.github\copilot-handshake.md`

**Verificação:**
```powershell
Test-Path .github\copilot-handshake.md
# Esperado: True
```

**Exit codes:**
- **0:** Template gerado com sucesso

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 95-103), `docs/scripts/_ia/generators/generate-handshake-template.py`

---

#### generate-invocation-examples.py

**Propósito:** Gera exemplos de invocação para CI/CD a partir de EXEC_TASK files

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\generators\generate-invocation-examples.py
```

**Saída:** `docs\_ai\_specs\invocation-examples.yml`

**Verificação:**
```powershell
Get-Content docs\_ai\_specs\invocation-examples.yml | Select-String "task"
# Esperado: task: models_validation
```

**Exit codes:**
- **0:** Exemplos gerados com sucesso

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 105-113), `docs/scripts/_ia/generators/generate-invocation-examples.py`

---

#### generate-checklist-yml.py

**Propósito:** Converte checklist markdown em workflow estruturado YAML

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\generators\generate-checklist-yml.py
```

**Saída:** `docs\_ai\_specs\checklist-models.yml`

**Verificação:**
```powershell
Get-Content docs\_ai\_specs\checklist-models.yml | Select-String "STEP_"
# Esperado: STEP_0, STEP_1, STEP_2
```

**Exit codes:**
- **0:** Checklist YAML gerado com sucesso

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 115-123), `docs/scripts/_ia/generators/generate-checklist-yml.py`

---

### 2.3 Validadores

#### validate-approved-commands.py

**Propósito:** Verifica se scripts usam apenas comandos whitelisted

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\validators\validate-approved-commands.py
```

**Saída:** Exit code 0 (pass) ou 1 (violations)

**Verificação:**
```powershell
$LASTEXITCODE
# 0 = todos os comandos aprovados
# 1 = comandos não autorizados encontrados
```

**Exit codes:**
- **0:** Todos os comandos são aprovados
- **1:** Comandos não autorizados encontrados (ver output para detalhes)

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 71-79), `docs/scripts/_ia/validators/validate-approved-commands.py`

---

#### validate-quality-gates.py

**Propósito:** Enforce complexidade ciclomática (radon cc)

**Comando:**
```powershell
# CWD: repo root (C:\HB TRACK)
python scripts\_ia\validators\validate-quality-gates.py "Hb Track - Backend\app"
```

**Saída:** Exit code 0 (compliant) ou 1 (violations)

**Verificação:**
```powershell
# Output mostra métricas Radon
# Exemplo: [FAIL] Complexity 12 > 10: app/models/athletes.py
```

**Exit codes:**
- **0:** Código está em conformidade com quality gates
- **1:** Violações de complexidade detectadas

**Evidência:** `IMPLEMENTATION_SUMMARY.md` (linhas 81-89), `docs/scripts/_ia/validators/validate-quality-gates.py`

---

## 3. Fluxo de Troubleshooting

### Exit Code 0 (Success)
✅ **Ação:** Prosseguir para próximo passo

---

### Exit Code 1 (Crash)

**Sintomas:**
- Traceback Python
- `FileNotFoundError`
- `ModuleNotFoundError`

**Diagnóstico:**
```powershell
# 1. Verificar dependências
pip list | Select-String "pyyaml|radon"

# 2. Verificar paths
Get-Location
# Deve estar em C:\HB TRACK (repo root) ou C:\HB TRACK\Hb Track - Backend

# 3. Verificar versões
python --version  # Esperado: 3.9+
pwsh --version
```

**Soluções:**
1. Instalar dependências: `pip install -r scripts\_ia\requirements.txt`
2. Corrigir CWD: `Set-Location "C:\HB TRACK"` ou `cd "Hb Track - Backend"`
3. Consultar: `docs\references\exit_codes.md`

**Evidência:** `docs\_ai\_maps\troubleshooting-map.json` (exit_codes.1)

---

### Exit Code 2 (Parity)

**Sintomas:**
- `[PARITY] Structural differences detected`
- Diff de colunas/constraints/índices

**Causas comuns:**
- Migration pendente não aplicada
- Model alterado sem migration correspondente
- Schema PostgreSQL alterado manualmente (fora de Alembic)

**Soluções:**
1. Ver diffs: `Get-Content docs\_generated\parity_report.json`
2. Aplicar migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`
3. Consultar: `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md`

**Evidência:** `docs\_ai\_maps\troubleshooting-map.json` (exit_codes.2)

---

### Exit Code 3 (Guard)

**Sintomas:**
- `[GUARD] Baseline violation detected`
- Arquivo protegido foi modificado

**Causas comuns:**
- Modificação intencional em arquivo guardado (ex: `app/routes/teams.py`)
- Efeito colateral de autogen

**Soluções:**
```powershell
# 1. Verificar modificações
git diff app/routes/teams.py

# 2. Se intencional: atualizar baseline
.\venv\Scripts\python.exe scripts\agent_guard.py snapshot baseline

# 3. Se acidental: reverter
git restore -- app/routes/teams.py
```

**Consultar:** `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md`

**Evidência:** `docs\_ai\_maps\troubleshooting-map.json` (exit_codes.3)

---

### Exit Code 4 (Requirements)

**Sintomas:**
- `[REQUIREMENTS] Violations detected`
- Tipo incompatível
- Nullable mismatch
- Missing server_default

**Exemplos de violações:**
```
expected=Integer got=String
expected=NOT NULL got=omitted
expected=default_literal:false got=None
```

**Soluções:**
1. Ver violações detalhadas no output do script
2. Corrigir model manualmente:
   ```python
   # Antes
   is_active: Mapped[bool] = mapped_column(Boolean)
   
   # Depois (com server_default)
   is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
   ```
3. Consultar: `docs\references\model_requirements_guide.md`

**Evidência:** `docs\_ai\_maps\troubleshooting-map.json` (exit_codes.4)

---

## 4. Workflow Completo: Regenerar Artefatos AI

Execute na ordem exata para manter consistência:

```powershell
# 0. Garantir CWD correto
Set-Location "C:\HB TRACK"
Get-Location  # Verificar

# 1. Gerar comandos aprovados
python scripts\_ia\extractors\extract-approved-commands.py
# Verificar: Test-Path docs\_ai\_context\approved-commands.yml

# 2. Gerar troubleshooting map
python scripts\_ia\extractors\extract-troubleshooting.py
# Verificar: Test-Path docs\_ai\_maps\troubleshooting-map.json

# 3. Gerar handshake template
python scripts\_ia\generators\generate-handshake-template.py
# Verificar: Test-Path .github\copilot-handshake.md

# 4. Gerar invocation examples
python scripts\_ia\generators\generate-invocation-examples.py
# Verificar: Test-Path docs\_ai\_specs\invocation-examples.yml

# 5. Gerar checklist YAML
python scripts\_ia\generators\generate-checklist-yml.py
# Verificar: Test-Path docs\_ai\_specs\checklist-models.yml

# 6. Validar comandos (CI check)
python scripts\_ia\validators\validate-approved-commands.py
# Esperado: Exit 0 (se não houver violations)

# 7. Validar quality gates
python scripts\_ia\validators\validate-quality-gates.py "Hb Track - Backend\app"
# Esperado: Exit 0 (se código estiver conforme)
```

**Exit code propagation:**
- Se qualquer script retornar exit != 0, PARE e investigue
- Não prossiga para próximo passo sem resolver o erro atual

---

## 5. Integração com Desenvolvimento

### Antes de Commit

```powershell
# 1. Garantir que repo está limpo
git status --porcelain
# Deve estar vazio OU apenas mudanças intencionais

# 2. Rodar validadores
python scripts\_ia\validators\validate-approved-commands.py
python scripts\_ia\validators\validate-quality-gates.py "Hb Track - Backend\app"

# 3. Verificar exit codes (todos devem ser 0)
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Validations failed. Fix issues before committing." -ForegroundColor Red
    exit 1
}
```

### Após Atualizar Canon

```powershell
# 1. Regenerar artefatos AI (ver seção 4)
# ... (comandos da seção 4)

# 2. Commitar artefatos gerados junto com canon atualizado
git add docs\_ai\_context\approved-commands.yml
git add docs\_ai\_maps\troubleshooting-map.json
git add docs\_ai\_specs\*.yml
git add .github\copilot-handshake.md
git commit -m "chore: regenerate AI artifacts after canon update"
```

---

## 6. PENDENTES

### PENDENTE 1: Validar agents autônomos

**Ação:** Listar conteúdo de `scripts\_ia\agents\` e documentar uso

```powershell
Get-ChildItem "scripts\_ia\agents\" -File
# TODO: Adicionar documentação conforme implementação
```

### PENDENTE 2: Confirmar quality-gates.yml

**Ação:** Verificar se arquivo existe

```powershell
Test-Path docs\_ai\_specs\quality-gates.yml
# Se False: criar template conforme ADR-016
```

---

## 7. Documentação Complementar

| Documento | Caminho | Descrição |
|-----------|---------|-----------|
| **Start Here** | `docs\_canon\00_START_HERE.md` | Ponto de entrada da documentação canônica |
| **Approved Commands** | `docs\_canon\08_APPROVED_COMMANDS.md` | Lista completa de comandos aprovados |
| **Troubleshooting** | `docs\_canon\09_TROUBLESHOOTING_GUARD_PARITY.md` | Guia de resolução de problemas |
| **Exit Codes** | `docs\references\exit_codes.md` | Referência completa de códigos de saída |
| **Workflows** | `docs\_canon\03_WORKFLOWS.md` | Fluxos de trabalho detalhados |
| **Implementation Summary** | `IMPLEMENTATION_SUMMARY.md` | Resumo da infraestrutura AI (9 scripts implementados) |

---

## 8. Referências de Evidência

Todos os comandos e procedures neste documento são baseados em:
- `IMPLEMENTATION_SUMMARY.md` (linhas 1-256)
- Código-fonte em `docs/scripts/_ia/**/*.py`
- Artefatos gerados em `docs/_ai/`
- Documentação canônica em `docs/_canon/`

---

**Última atualização:** 2026-02-12  
**Autor:** GitHub Copilot Agent  
**Baseado em:** IMPLEMENTATION_SUMMARY.md e artefatos do repositório `Davisermenho/Hb_Track`
