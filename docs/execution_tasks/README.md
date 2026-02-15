---
description: Index and guide for execution tasks (EXEC_TASK files)
---

# Execution Tasks

Tarefas executáveis derivadas de ADRs. Use quando você quer **"fazer"** algo, não apenas "decidir".

Cada EXEC_TASK é um plano passo-a-passo com pré-requisitos, gates, e critérios de conclusão.

---

## 🚀 Quick Start

### Para uma Nova Tarefa:
1. **Scaffold**: `python scripts/bootstrap_task.py TASK-ID --title "Título" --scope Area`
2. **Executar**: Realize o trabalho técnico.
3. **Documentar**: Atualize `status` e `notes_short` no `event.json` da tarefa.
4. **Indexar**: `python scripts/compact_exec_logs.py --write` para atualizar o Board.

### Para Executar uma Tarefa Existente:
1. **Escolha uma tarefa abaixo**
2. **Valide pré-requisitos** (seção "Checklist")
3. **Siga Fases 1-4** (Prep → Execute → Validate → Commit)
4. **Obtenha suporte** em Troubleshooting se falhar

---

## 📏 Line Endings & Determinism

Para evitar falhas de "drift" no CI (**hv_check**) causadas por diferenças entre Windows (CRLF) e Linux (LF):

1. **Configuração**: O repositório usa `.gitattributes` e `.editorconfig` para forçar **LF** em arquivos Python, JSON e Markdown.
2. **Correção Automática**: O comando `python scripts/compact_exec_logs.py --write` normaliza as quebras de linha dos artefatos.
3. **Git Config**: Se persistirem problemas, use `git config core.autocrlf input`.

---

## � Troubleshooting: "hv_check fail" (CI Failure)

Se o gate de **Human Visibility Layer** falhar no GitHub Actions, siga este guia rápido:

1. **Identifique a falha**: `python scripts/compact_exec_logs.py --check` (mostra o drift).
2. **Sincronize**: `python scripts/compact_exec_logs.py --write` (regenera índices e normaliza sumários).
3. **Valide**: `python scripts/compact_exec_logs.py --check` (deve retornar Exit 0).
4. **Revise**: `git diff` para garantir que apenas artefatos de execução/docs foram alterados.
5. **Commit**: `git add . && git commit -m "chore(docs): fix human visibility layer"`.

---

## �📋 Available Tasks

### 1. `EXEC_TASK_ADR_MODELS_001.md` — Fix Models ↔ DB Divergências

**Status:** 🟢 **READY** (última validação: 2026-02-10)

**What:**
- Scan 65 tables para divergências estruturais (Model vs DB schema)
- Auto-generate patches via SQLAlchemy autogen
- Validar que models agora passam em gate
- Commit tudo com baseline refresh

**Duration:** 4-6 horas (parallelizável)

**Prerequisites:**
- PowerShell 5.1
- Python 3.11+ with venv
- Postgres running (port 5433)
- FastAPI running (port 8000)
- Repo clean (`git status --porcelain` empty)

**Phases:**
1. Prep: Validate env, SSOT refresh, audit 65 tables
2. Execute: Auto-gate em lote (models_batch.ps1)
3. Validate: Smoke tests (all PASS)
4. Commit: baseline snapshot + push

**Next:** Start this if:
- You see "FAIL" in requirements scan
- You modified models and need to validate
- You want 100% Model↔DB alignment

---

### 2. `EXEC_TASK_ADR_INV_TRAIN_002.md` — Install Training Invariants

**Status:** 🟡 **IN PROGRESS** (pending completion of MODELS_001)

**What:**
- Batch install 5-10 training invariants from candidates/backlog
- Each invariant: SPEC + code + tests + gate pass
- Update SSOT (INVARIANTS_TRAINING.md)
- Final validation (verify_invariants_tests.py passes)

**Duration:** 2-3 horas per invariant

**Prerequisites:**
- ✅ EXEC_TASK_ADR_MODELS_001 completo (models stable)
- Backlog candidates defined ("training_invariants_candidates.md")
- Protocol understood (INVARIANTS_AGENT_PROTOCOL.md)

**Phases:**
1. Prep: Load candidates, pick next invariant
2. Execute: Write SPEC, code, tests
3. Validate: Gate passes, no regressions
4. Commit: Update SSOT + CHANGELOG

**Next:** Start this when:
- MODELS_001 ✅ done
- You have new training rules to enforce

---

## 🔗 Dependency Graph

```
EXEC_TASK_ADR_MODELS_001 (Models)
         ↓ 
    (prerequisite for)
         ↓
EXEC_TASK_ADR_INV_TRAIN_002 (Invariants)
         ↓
    (prerequisite for)
         ↓
[Future] EXEC_TASK_ADR_DEPLOY_* (Release/Deploy)
```

---

## ✅ Pre-Execution Checklist

Run this BEFORE starting ANY exec task:

```powershell
# 1. PowerShell version
$PSVersionTable.PSVersion.Major  # Must be 5

# 2. Venv exists & valid
Test-Path "Hb Track - Backend\venv\Scripts\python.exe"

# 3. Python 3.11+
& "Hb Track - Backend\venv\Scripts\python.exe" --version

# 4. Dependencies installed
& "Hb Track - Backend\venv\Scripts\pip.exe" list | grep sqlalchemy

# 5. Postgres running (port 5433)
Test-NetConnection localhost -Port 5433

# 6. FastAPI running (port 8000)  [optional for some tasks]
Test-NetConnection localhost -Port 8000

# 7. Repo clean
git status --porcelain  # Must be empty

# 8. Baseline exists
Test-Path ".hb_guard\baseline.json"

# 9. SSOT recent (age < 24h)
ls "docs\_generated\_core\schema.sql" | select LastWriteTime
```

If ANY check fails: **ABORT** and fix (see Troubleshooting).

---

## 📊 Status Board

| Task | Status | Last Run | Duration | Next Action |
|------|--------|----------|----------|-------------|
| **MODELS_001** | 🟢 READY | 2026-02-10 | 4-6h | Can start now |
| **INV_TRAIN_002** | 🟡 IN PROGRESS | — | 2-3h | When MODELS_001 ✅ |

---

## 🆘 Troubleshooting

| Problem | Solution | Docs |
|---------|----------|------|
| PowerShell version mismatch | Ensure PS 5.1 (`$Host.Version`) | `docs/_canon/03_WORKFLOWS.md` |
| Venv not found | Activate from Backend root: `. .\venv\Scripts\Activate.ps1` | `docs/_ai/INV_TASK_TEMPLATE.md` |
| Postgres connection fails | `docker-compose up -d postgres` | `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md` |
| FastAPI timeout | Start: `python -m uvicorn app.main:app --port 8000` | `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md` |
| Git status not clean | `git restore .` then `git clean -fd` | `docs/_canon/10_GIT_PR_MERGE_WORKFLOW.md` |
| Baseline mismatch | `python scripts/agent_guard.py snapshot --root . --out .hb_guard/baseline.json` | `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md` |
| Requirements FAIL | Run `/parity-fix <table>` in Copilot | `docs/_ai/06_AGENT-PROMPTS.md` |
| Gate falha mysteriously | Check CHANGELOG.md for recent changes | `docs/execution_tasks/CHANGELOG.md` |

Full guide: `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md`

---

## 📝 How to Add New Exec Task

1. **Write ADR** (decision document): `docs/ADR/XXX-ADR-*.md`
2. **Create EXEC_TASK** from template: `docs/execution_tasks/EXEC_TASK_ADR_*.md`
   - Copy from `docs/_ai/INV_TASK_TEMPLATE.md`
   - Fill in Phases 1-4
   - Define gates + smoke tests
3. **Update this README** with status + duration
4. **Link in Dependency Graph** if prerequisite/successor relationship exists
5. **Commit both** (ADR + EXEC_TASK) together

---

## 📚 Reference

- **Template:** `docs/_ai/INV_TASK_TEMPLATE.md`
- **Workflows:** `docs/_canon/03_WORKFLOWS.md`
- **Troubleshooting:** `docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md`
- **Approved Commands:** `docs/_canon/08_APPROVED_COMMANDS.md`
- **Prompts:** `docs/_ai/06_AGENT-PROMPTS.md` (use with Copilot)
- **Changelog:** `CHANGELOG.md` (in this directory)
- **Execution Log:** `EXECUTIONLOG.md` (in this directory)
