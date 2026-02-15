# ARCH_REQUEST — AUDITORIA TÉCNICA ENTERPRISE DE SCRIPTS E DOCUMENTAÇÃO

Status: APPROVED_FOR_EXECUTION
Version: 1.0.0
Task ID: AR-2026-02-13-SCRIPTS-DOCS-AUDIT
Priority: HIGH
Budget: MAX_COMMANDS=40 / MAX_TIME=180min

---

## 1) CONTEXTO

Problema: o monorepo possui múltiplos diretórios de scripts e documentação com maturidade operacional heterogênea.

Objetivo Final: auditar todos os diretórios com nome de scripts/documentação, definir destino de cada arquivo por utilidade operacional, padronizar contrato mínimo dos scripts incorporáveis e organizar sem quebra.

---

## 2) OBJETIVOS (MUST)

- MUST-01: Inventário completo dos diretórios de scripts/documentação no monorepo.
- MUST-02: Classificação por arquivo em exatamente uma categoria:
  - INCORPORAR
  - REFATORAR_ANTES_DE_INCORPORAR
  - DIVIDA_TECNICA
  - ARQUIVAR
- MUST-03: Para entrar no `SCRIPTS_GUIDE.md`, script deve suportar interface padronizada (`--tenant-id`, `--dry-run`) e logs estruturados JSON.
- MUST-04: Script de correção/migração só é Enterprise se idempotente.
- MUST-05: Proibido deletar fisicamente; arquivar em `_archived/`.
- MUST-06: Atualizar `docs/_canon/00_START_HERE.md` quando houver impacto de roteamento.

---

## 3) SSOT / AUTORIDADE

- `docs/_canon/AI_KERNEL.md`
- `docs/_canon/ARCH_REQUEST_DSL.md`
- `docs/_canon/_agent/TASK_BRIEF.md`
- `docs/_canon/_agent/AI_PROTOCOL_CHECKLIST.md`
- `docs/_canon/08_APPROVED_COMMANDS.md`
- `docs/_canon/00_START_HERE.md`

---

## 4) SCOPE (ALLOWLIST)

### Read Access
- `scripts/**`
- `docs/**`
- `Hb Track - Backend/scripts/**`
- `Hb Track - Fronted/scripts/**`

### Write Access
- `docs/_canon/_arch_requests/**`
- `docs/_canon/SCRIPTS_GUIDE.md`
- `docs/_canon/00_START_HERE.md`
- `.gitignore`
- Criação de estruturas `_archived/**` (quando aplicável)

### Proibido
- Delete físico de arquivos auditados
- Edição manual de artefatos gerados SSOT
- Execução de comandos fora da whitelist sem autorização explícita

---

## 5) DELTA ESTRUTURAL

- Inclusão de ARCH_REQUEST canônica da auditoria
- Inclusão de `SCRIPTS_GUIDE.md` canônico
- Inclusão de relatório de auditoria por arquivo
- Atualização de roteamento em `00_START_HERE.md`
- Política explícita de `_archived/` no `.gitignore`

---

## 6) EXECUTION PLAN

1. Preflight (CWD + integridade de docs canônicos)
2. Inventário de diretórios com nome `scripts` e documentação
3. Classificação técnica dos arquivos
4. Definição de scripts críticos para smoke tests
5. Materialização de guias/contratos
6. Preparação de reorganização segura (`_archived/`)

---

## 7) GATES

- GATE-A (DSL): ARCH_REQUEST estruturalmente válida
- GATE-B (Contrato): scripts incorporáveis com interface + JSON logs
- GATE-C (Idempotência): fix/migração com repetibilidade comprovada
- GATE-D (Compliance): sem delete físico; apenas `_archived/`
- GATE-E (Integridade): scripts críticos seguem operacionais

---

## 8) ACCEPTANCE CRITERIA (BINARY)

- [ ] Inventário completo de escopo realizado
- [ ] Cada arquivo com decisão e justificativa
- [ ] `SCRIPTS_GUIDE.md` criado com contrato mínimo
- [ ] Idempotência tratada para scripts de fix/migração
- [ ] Política de arquivamento `_archived/` registrada
- [ ] `00_START_HERE.md` alinhado com novos artefatos

---

## 9) STOP CONDITIONS

- Comando fora de `08_APPROVED_COMMANDS.md` sem autorização
- Tentativa de delete físico
- Ausência de critérios para provar idempotência
- Evidência de quebra em script crítico

---

## 10) ROLLBACK PLAN

- Reverter alterações de docs e política de arquivamento
- Restaurar estrutura anterior de roteamento
- Revalidar scripts críticos

---

## 11) TEST PLAN

### TEST_FILES_REQUIRED
- `docs/_canon/_arch_requests/AR-2026-02-13-SCRIPTS-DOCS-AUDIT.md`
- `docs/_canon/SCRIPTS_GUIDE.md`
- `docs/_canon/_arch_requests/AUDIT_SCRIPTS_DOCS_REPORT.md`
- `.gitignore`
- `docs/_canon/00_START_HERE.md`

### MIN_ASSERTS
- assert: zero delete físico de arquivos auditados
- assert: scripts incorporáveis com interface mínima padronizada
- assert: política de logs JSON definida no guia
- assert: estratégia de idempotência documentada

---

## 12) ARCHITECT AUTHORIZATION

Checklist validado. Determinism Score: 4/5. Task apta para execução.
