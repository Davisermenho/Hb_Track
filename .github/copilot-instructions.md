---
description: HB Track - Handball System Project context and mandatory execution rules for Agent/Copilot. Never forget this ruleset, it is the foundation for all your actions in this project. Always refer to the canonical documentation for any technical question.
applyTo: '**'
---

## PORTA ÚNICA: Camada Canônica Docs

**Source of truth: docs/_canon/AI_KERNEL.md**

**Para QUALQUER consulta técnica, comece AQUI:** `docs/_canon/00_START_HERE.md` **(OBRIGATÓRIO)**

* Sempre ler **_INDEX.md** (`docs/_ai/_INDEX.md`) para ter o contexto necessário antes de qualquer ação. **(OBRIGATÓRIO)**

* Para workflows **LEIA** o passo-a-passo em `docs/_canon/03_WORKFLOWS.md`. **(OBRIGATÓRIO)**

* NÃO CRIE ARQUIVOS NO REPO SEM AUTORIZAÇÃO EXPLICITA. SE PRECISAR, CRIE EM %TEMP% E DEPOIS PEÇA AO HUMANO PARA MOVER PARA O LOCAL CORRETO APÓS VALIDAÇÃO. **(OBRIGATÓRIO)**
* Atue como um desenvolvedor experiente do projeto, não como um agente genérico. O contexto específico do projeto é crucial para decisões técnicas corretas. **(OBRIGATÓRIO)**

* ** Esta camada orienta para documentação correta conforme sua intenção:

- **O que confiar (precedência):** → `docs/_canon/01_AUTHORITY_SSOT.md` (DB > Service > OpenAPI > Docs)
- **Quero fazer X, por onde?: → `docs/_canon/02_CONTEXT_MAP.md` (intenção → docs → evidência)
- **Workflow/checklist:** → `docs/_canon/03_WORKFLOWS.md` (passo-a-passo operacional)
- **Arquivos gerados:** → `docs/_canon/04_SOURCES_GENERATED.md` (schema.sql, openapi.json, reports)

**Regra obrigatória:** Toda resposta técnica deve citar (a) um documento canônico e (b) uma validação com evidência (código, schema.sql, openapi.json, parity_report.json ou ADR).

---
**Abortar imediatamente se:**
- PowerShell não é versão 5.1
- Venv não existe ou está corrompido
- Python não é 3.11+
- Dependências (sqlalchemy/alembic) não instaladas
- Baseline (.hb_guard/baseline.json) não existe
- Schema.sql desatualizado ou ausente
---

### Docs Organization

**Canonical Authority:**
- `docs/_canon/` — autoridade + navegação (START_HERE, SSOT, workflows, troubleshooting)
- `docs/_ai/` — guidelines operacionais para agente + protocol + guardrails

**SSOT Artifacts (Protected):**
- `docs/_generated/_core/` — schema.sql, openapi.json, parity_report.json, alembic_state.txt, manifest.json
- **Use env var:** `HB_DOCS_GENERATED_DIR` para customizar (default: `_generated`)

**Debug/Scratch (Excluded from Index):**
- `docs/_generated/_scratch/` — debug artifacts (excluded via .gitignore)
- `docs/scripts/_archive/` — archived/legacy scripts (excluded via .gitignore)

**Reference:**
- `docs/ADR/` — architecture decisions (decisões importantes, não executáveis)
- `docs/execution_tasks/` — EXEC_TASK files (tarefas executáveis com gates)
- `docs/02_modulos/` — módulos por feature (athletes, training, teams, etc)

