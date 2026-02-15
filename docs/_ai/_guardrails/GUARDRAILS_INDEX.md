# Guardrails Index — HB Track AI Agent Protection

> **Status:** OPERATIONAL  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13  
> **Applies To:** AI Agents (execution constraints)
>
> **NATUREZA DESTE ARQUIVO**: Entry point único para todas as políticas de guardrails do HB Track.  
> **PRECEDÊNCIA**: Este arquivo é subordinado a [`docs/_canon/00_START_HERE.md`](../../_canon/00_START_HERE.md) (LEVEL 1 CANONICAL). Em caso de conflito, canonical docs vencem.
>
> **Hierarquia:**
> - **LEVEL 1** (CANONICAL): [`00_START_HERE.md`](../../_canon/00_START_HERE.md), [`GOVERNANCE_MODEL.md`](../../_canon/GOVERNANCE_MODEL.md)
> - **LEVEL 2** (OPERATIONAL): Este arquivo (guardrails index) + módulos específicos abaixo
> - **LEVEL 3** (GENERATED): `schema.sql`, `openapi.json`, `parity_report.json`, `baseline.json` (LOCAL)

---

## 🎯 Propósito

Guardrails protegem agentes AI contra estados inválidos, alucinação, e drift documental. São **fail-fast rules** que:
- Bloqueiam execução quando pré-condições não são atendidas
- Forçam validação antes de mudanças destrutivas
- Garantem conformidade com SSOT (Single Source of Truth)
- Previnem commits de artefatos temporários/locais

**Princípio:** Melhor falhar rápido (exit != 0) do que prosseguir em estado inconsistente e corromper repositório.

---

## 📚 Guardrails por Domínio

### 1. Gate-Specific Guardrails (Model Pipeline)

Políticas específicas dos 3 gates principais (baseline, parity, requirements):

#### **1.1. Baseline Policy**
**Arquivo:** [`GUARDRAIL_POLICY_BASELINE.md`](GUARDRAIL_POLICY_BASELINE.md)  
**Domínio:** `.hb_guard/baseline.json` (artefato de sessão local)  
**Regra Crítica:** Baseline NUNCA commitado (`.gitignore` proteção obrigatória)

**Quick Reference:**
- ✅ **Obrigatório**: `.gitignore` contém `.hb_guard/`
- ✅ **Obrigatório**: `git status --porcelain | grep baseline.json` retorna vazio
- ❌ **Proibido**: `git add .hb_guard/baseline.json`
- 🔄 **Recovery**: `git restore --staged .hb_guard/baseline.json`

**Quando consultar:** Antes de snapshot baseline; se baseline apareceu em `git status`; se pre-commit hook bloqueou commit.

---

#### **1.2. Parity Policy**
**Arquivo:** [`GUARDRAIL_POLICY_PARITY.md`](GUARDRAIL_POLICY_PARITY.md)  
**Domínio:** Conformidade estrutural entre `schema.sql` (SSOT) e SQLAlchemy models  
**Regra Crítica:** Schema.sql vence sempre (DB → Code direction)

**Quick Reference:**
- ✅ **Obrigatório**: `inv.ps1 refresh` antes de parity scan
- ✅ **Obrigatório**: `parity_gate.ps1` retorna EXIT 0 (zero DIFFs)
- ❌ **Proibido**: Editar models sem parity validation
- 🔄 **Recovery**: Consultar `parity_report.json` → corrigir model.py ou schema.sql → rerun

**Quando consultar:** Antes de editar models; quando `models_autogen_gate.ps1` retorna EXIT 2; se `parity_report.json` mostra DIFFs.

---

#### **1.3. Requirements Policy**
**Arquivo:** [`GUARDRAIL_POLICY_REQUIREMENTS.md`](GUARDRAIL_POLICY_REQUIREMENTS.md)  
**Domínio:** Validação de regras de negócio/constraints em models (vs schema.sql)  
**Regra Crítica:** Profiles determinam severidade (strict > fk > lenient)

**Quick Reference:**
- ✅ **Obrigatório**: Profile correto escolhido (`strict` default; `fk` para teams/seasons)
- ✅ **Obrigatório**: `model_requirements.py` retorna EXIT 0
- ❌ **Proibido**: Bypassar EXIT 4 (requirements violation)
- 🔄 **Recovery**: Parser output → corrigir validator/default/constraint → rerun

**Quando consultar:** Antes de gate final; quando `model_requirements.py` retorna EXIT 4; se precisar entender profiles (strict/fk/lenient).

---

### 2. Operational Guardrails (General)

Políticas operacionais multi-domínio (DevOps, Repo, Model Pipeline, Docs):

#### **2.1. Agent Guardrails (Core)**
**Arquivo:** [`AGENT_GUARDRAILS.md`](../_context/AGENT_GUARDRAILS.md)  
**Domínio:** DevOps, Repository, Model Pipeline, Documentation  
**Regra Crítica:** Fail-fast em pré-condições (PowerShell 5.1+, Python 3.11+, venv válido, repo limpo)

**Quick Reference:**
- ✅ **DevOps**: PS 5.1+, Python 3.11+, venv válido, deps instaladas (sqlalchemy/alembic)
- ✅ **Repository**: Repo limpo antes de gates (exceto read-only), review `git diff`, nunca `git reset --hard` sem autorização
- ✅ **Model Pipeline**: Nunca ignorar exit != 0, nunca snapshot sem gates OK, nunca editar regiões `HB-AUTOGEN`
- ✅ **Documentation**: Nunca criar temporários no repo, nunca editar `.gitignore` sem ADR, nunca mover SSOT sem workflow

**Quando consultar:** Antes de iniciar qualquer tarefa operacional; se pre-commit hooks falharem; se comandos retornarem exit != 0.

---

### 3. Invariants Guardrails (Training Module)

Políticas específicas de invariantes do módulo Training:

#### **3.1. Invariants Agent Guardrails**
**Arquivo:** [`INVARIANTS_AGENT_GUARDRAILS.md`](../INVARIANTS_AGENT_GUARDRAILS.md)  
**Domínio:** Gates de invariantes (`INV-TRAIN-XXX`), exit codes, helper canônico para testes DB  
**Regra Crítica:** SSOT vence (openapi.json, schema.sql, alembic_state.txt); nunca promover golden com VERIFY_EXIT != 0

**Quick Reference:**
- ✅ **SSOT**: `openapi.json`, `schema.sql`, `alembic_state.txt`, `INVARIANTS_TRAINING.md`, `verify_invariants_tests.py`
- ✅ **Exit Codes**: 0=PASS, 1=FAIL (corrigir), 3=DRIFT (revisar + promover)
- ✅ **Loop Obrigatório**: Implementar → gate → EXIT != 0? corrigir → repeat
- ❌ **Proibido**: Promover golden com VERIFY_EXIT != 0 ou PYTEST_EXIT != 0
- ❌ **Proibido**: Acessar `orig.diag` ou `orig.__cause__` diretamente (usar helper `assert_pg_constraint_violation`)

**Quando consultar:** Ao trabalhar com invariantes (INVARIANTS_TRAINING.md); quando `inv.ps1 gate` retorna EXIT 3 (drift); se testes DB precisam assert de constraints Postgres.

---

## 🚦 Workflow de Consulta (Decision Tree)

```
┌─────────────────────────────────────────┐
│ Qual tipo de tarefa você está fazendo? │
└─────────────────────────────────────────┘
           │
           ├─ Editar models SQLAlchemy
           │  └─> Consultar: Parity + Requirements + Baseline
           │
           ├─ Validar conformidade schema.sql ↔ models
           │  └─> Consultar: Parity
           │
           ├─ Rodar gate (models_autogen_gate.ps1)
           │  └─> Consultar: Baseline + Parity + Requirements
           │
           ├─ Trabalhar com invariantes (INV-TRAIN-XXX)
           │  └─> Consultar: Invariants Agent Guardrails
           │
           ├─ Commit/Push/PR
           │  └─> Consultar: Agent Guardrails (Repository)
           │
           ├─ Setup environment (venv, deps, PS version)
           │  └─> Consultar: Agent Guardrails (DevOps)
           │
           └─ Entender exit codes (0/1/2/3/4)
              └─> Consultar: exit_codes.md + Parity/Requirements (específico)
```

---

## 📋 Checklist Pré-Execução (Universal)

Antes de **qualquer** tarefa operacional que modifique código/docs:

- [ ] **DevOps Checks**:
  - [ ] PowerShell 5.1+ (`$PSVersionTable.PSVersion.Major -ge 5`)
  - [ ] Python 3.11+ (`& venv\Scripts\python.exe --version`)
  - [ ] Venv válido (`Test-Path "C:\HB TRACK\Hb Track - Backend\venv\Scripts\python.exe"`)
  - [ ] Dependências instaladas (`& venv\Scripts\python.exe -m pip list | Select-String "sqlalchemy|alembic"`)

- [ ] **Repository Checks**:
  - [ ] CWD correto (`Get-Location` retorna repo root ou backend root conforme comando)
  - [ ] Repo limpo (`git status --porcelain` retorna vazio, exceto read-only operations)
  - [ ] SSOT atualizado (`inv.ps1 refresh` executado se `manifest.json` > 5min)

- [ ] **Documentation Checks**:
  - [ ] Consultou [`00_START_HERE.md`](../../_canon/00_START_HERE.md) para workflow canônico
  - [ ] Verificou [`08_APPROVED_COMMANDS.md`](../../_canon/08_APPROVED_COMMANDS.md) se comando não listado aqui

---

## 🔗 Documentação Relacionada

**LEVEL 1 (CANONICAL):**
- [`00_START_HERE.md`](../../_canon/00_START_HERE.md) — Porta única de navegação
- [`01_AUTHORITY_SSOT.md`](../../_canon/01_AUTHORITY_SSOT.md) — Precedência de fontes
- [`05_MODELS_PIPELINE.md`](../../_canon/05_MODELS_PIPELINE.md) — Pipeline model ↔ schema
- [`08_APPROVED_COMMANDS.md`](../../_canon/08_APPROVED_COMMANDS.md) — Comando whitelist
- [`09_TROUBLESHOOTING_GUARD_PARITY.md`](../../_canon/09_TROUBLESHOOTING_GUARD_PARITY.md) — Exit codes + diagnóstico

**LEVEL 0 (GOVERNANCE):**
- [`GOVERNANCE_MODEL.md`](../../_canon/GOVERNANCE_MODEL.md) — Hierarquia documental (LEVEL 0-4)
- [`AI_ARCH_EXEC_PROTOCOL.md`](../../_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md) — Architect vs Executor protocol
- [`AI_PROTOCOL_CHECKLIST.md`](../../_canon/_agent/AI_PROTOCOL_CHECKLIST.md) — Pre-validation checklist

**LEVEL 3 (GENERATED):**
- `docs/_generated/schema.sql` — Database DDL (SSOT)
- `docs/_generated/openapi.json` — API contract (SSOT)
- `docs/_generated/parity_report.json` — Model-schema alignment report
- `docs/_generated/manifest.json` — Generation traceability
- `.hb_guard/baseline.json` — Guard state (LOCAL ONLY, never committed)

---

## 📊 Métricas de Compliance

**Objetivo:** 100% de operações seguem guardrails (zero violations).

**Tracking:**
- **Baseline violations**: `git log --all --grep="baseline.json"` deve retornar vazio
- **Parity violations**: `parity_report.json` → `"diffs": []` (zero DIFFs após gates)
- **Requirements violations**: `model_requirements.py` EXIT 0 em 100% das tabelas (profile correto)
- **Invariants violations**: `inv.ps1 all` EXIT 0 (zero drift não-intencional)

**Audit:** Consultar [`EXECUTIONLOG.md`](../../execution_tasks/EXECUTIONLOG.md) para histórico de guardrail enforcement.

---

## 🛠️ Troubleshooting

**Sintomas comuns e qual guardrail consultar:**

| Sintoma | Guardrail Relevante | Ação Imediata |
|---------|---------------------|---------------|
| `baseline.json` apareceu em `git status` | Baseline Policy | `git restore --staged .hb_guard/baseline.json` |
| `parity_gate.ps1` retorna EXIT 2 | Parity Policy | Consultar `parity_report.json` → corrigir DIFFs |
| `model_requirements.py` retorna EXIT 4 | Requirements Policy | Parser output → corrigir validator/default |
| Pre-commit hook bloqueou commit | Agent Guardrails (Repo) | Revisar `git diff` → verificar arquivos staged |
| `inv.ps1 gate` retorna EXIT 3 | Invariants Agent Guardrails | `inv.ps1 drift -WhatIf` → revisar → promover golden |
| PowerShell < 5.1 detectado | Agent Guardrails (DevOps) | Upgrade PowerShell ou use máquina compatível |
| Venv não encontrado | Agent Guardrails (DevOps) | Criar venv: `python -m venv "Hb Track - Backend\venv"` |
| `schema.sql` desatualizado (> 24h) | Parity Policy | `inv.ps1 refresh` (com autorização) |

---

## 🔄 Histórico de Mudanças

| Versão | Data | Mudança | Refs |
|--------|------|---------|------|
| 1.0.0 | 2026-02-13 | Criação do GUARDRAILS_INDEX.md (R3 remediation) | GOVERNANCE_AUDIT_REPORT.md Section 7 (R3) |

---

## 📝 Notas de Auditoria

**Governance Audit:** [GOVERNANCE_AUDIT_REPORT.md](../../_canon/_agent/GOVERNANCE_AUDIT_REPORT.md)  
**Audit Finding:** R3 — Guardrails fragmentation (5 separate files without unified entry point)  
**Resolution:** Created GUARDRAILS_INDEX.md as single navigation authority for all guardrail policies  
**Impact:** Clear navigation hierarchy; preserved granularity (files not merged); reduced ambiguity of which guardrail to consult

**Task ID:** T-555 (R3 — Consolidate Guardrails)  
**Branch:** `docs/gov-unify-001`  
**Validation:** All 5 guardrail files remain intact (not merged); index provides decision tree + quick reference for each
