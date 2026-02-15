# AGENT_GUARDRAILS.md

> **Parent:** [`../_guardrails/GUARDRAILS_INDEX.md`](../_guardrails/GUARDRAILS_INDEX.md) (Entry point único para todos os guardrails)  
> **Domain:** Operational Guardrails (DevOps, Repository, Model Pipeline, Documentation)  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13

## Descrição
Guardrails operacionais: limites, proibições, e comportamentos fail-fast que protegem o agente contra estados inválidos.

---

## Guardrails por Categoria

### DevOps Guardrails
- [ ] Não execute PowerShell versão < 5.1
- [ ] Não execute Python versão < 3.11
- [ ] Não prossiga sem venv válido
- [ ] Não prossiga sem dependências instaladas (sqlalchemy, alembic)

### Repository Guardrails
- [ ] Não rode gates/batch com repo sujo (exceto read-only)
- [ ] Não applique edições sem `git status --porcelain` antes
- [ ] Não comite sem `git diff` review
- [ ] Não use `git reset --hard` ou `git clean -fd` sem autorização explícita

### Model Pipeline Guardrails
- [ ] Não ignore exit code != 0 em gates
- [ ] Não snapshot baseline sem ALL gates OK
- [ ] Não edite regiões `HB-AUTOGEN`

### Documentation Guardrails
- [ ] Não crie artefatos temporários no repo
- [ ] Não edite `.gitignore` sem ADR
- [ ] Não mova/renomeie arquivos de SSOT sem workflow canônico

---

## TODO
- [ ] Criar checklist pré-execução
- [ ] Documentar recovery paths para cada guardrail violado
- [ ] Adicionar severity levels (BLOCKER/MAJOR/MINOR)
