# Governance Model (Canonical)

Status: CANONICAL  
Version: 1.1.0  
Last Updated: 2026-02-14  
Scope: Hierarquia normativa + precedência entre documentos/artefatos (anti-drift / anti-alucinação)

---

## Purpose

Definir uma hierarquia **determinística** para:

- resolver conflitos entre documentos sem ambiguidade
- evitar que docs operacionais sobrescrevam SSOT/ADRs
- reduzir alucinação por “escolha errada de fonte”

---

## Normative Hierarchy (Ordem de Precedência)

Em caso de conflito, o nível superior vence.

### LEVEL 0 — Constitution (Highest Authority)

- `docs/_canon/AI_KERNEL.md`
- ADRs: `docs/ADR/**`
- SSOT de estado (read-only): `docs/_generated/schema.sql`, `docs/_generated/openapi.json`, `docs/_generated/alembic_state.txt`

### LEVEL 1 — Canonical Documentation (Navigation Authority)

- Porta única: `docs/_canon/00_START_HERE.md`
- Canônicos operacionais: `docs/_canon/*.md`

### LEVEL 2 — Operational Documentation (Execution Guidance)

- Operação de agentes: `docs/_ai/**`
- Instruções e prompts versionados: `.github/instructions/**`, `.github/prompts/**`

### LEVEL 3 — Generated Artifacts (SSOT State)

- Artefatos gerados em `docs/_generated/**` (read-only; nunca editar manualmente)

### LEVEL 4 — Execution Artifacts / Evidence (Logs)

- Evidências e logs de execução (ex.: `docs/execution_tasks/**`, `docs/execution_tasks/artifacts/**`)

---

## Cross-Level Rules

1. LEVEL 0 overrides all: ADR/SSOT vencem qualquer doc inferior.
2. LEVEL 1 define navegação: agentes/humanos MUST começar em `docs/_canon/00_START_HERE.md`.
3. LEVEL 2 interpreta, não cria regra nova: docs operacionais não podem contradizer `docs/_canon/**` ou ADR.
4. LEVEL 3 é verdade de estado: gerados refletem o sistema; nunca editar manualmente.
5. LEVEL 4 é evidência: logs não têm autoridade normativa.

---

## Indices (Não confundir)

- Índice auto-gerado (lista de artefatos): `docs/_canon/AI_GOVERNANCE_INDEX.md` (DO NOT EDIT)
- Modelo de governança (este documento): `docs/_canon/GOVERNANCE_MODEL.md`

---

## Governance Workflow (Canônico)

1. Consultar `docs/_canon/00_START_HERE.md`
2. Se houver conflito/ambiguidade: aplicar esta hierarquia (LEVEL 0 → 4)
3. Executar usando somente comandos aprovados (`docs/_canon/08_APPROVED_COMMANDS.md`)
4. Produzir evidência (logs/artefatos) e declarar PASS/FAIL com base em gates
5. Se FAIL: escalar conforme protocolo aplicável

---

## Governance Map (Responsabilidades)

- `docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md`: separação de papéis + ciclo formal Architect/Executor.
- `docs/_canon/_agent/AI_PROTOCOL_CHECKLIST.md`: checklist pré-execução (determinismo antes de TASK).
- `docs/_canon/_agent/AI_TASK_VERSIONING_POLICY.md`: versionamento e rastreabilidade de tasks.
- `docs/_canon/_agent/AI_INCIDENT_RESPONSE_POLICY.md`: contenção/restauração em incidentes (SEV).

---

## Supremacy Rules

1. Protocol supremacy: se uma TASK conflitar com protocolo/camada superior, a TASK é inválida.
2. Incident override: durante incidente SEV-1, `AI_INCIDENT_RESPONSE_POLICY` assume precedência temporária sobre a execução.
3. SSOT supremacy: se qualquer doc conflitar com SSOT declarado (`docs/_generated/*`), SSOT prevalece.
4. Version integrity: nenhuma execução é válida sem rastreabilidade (task versionada + evidência mínima).

---

## Conflict Resolution Procedure

Se dois documentos conflitam:

1. Identificar os níveis (0-4)
2. Aplicar a precedência do nível superior
3. Tornar o conflito explícito (registrar)
4. Atualizar a fonte inferior (nova versão) para remover contradição

Nenhum conflito pode permanecer implícito.

---

## Governance Integrity Check

Toda execução deve conseguir responder objetivamente:

- Qual regra normativa está sendo aplicada?
- Qual documento fundamenta a decisão?
- Qual artefato SSOT/estado foi consultado?
- Qual foi o resultado formal (PASS/FAIL) e evidência associada?

Se não for possível responder: governança comprometida.

---

## Amendment Rule

Qualquer mudança neste modelo exige:

- incremento de versão
- justificativa
- atualização cruzada dos documentos impactados
- registro em changelog aplicável

---

## Role Boundaries

Matriz de papéis:

- `docs/_canon/_agent/AGENT_ROLE_MATRIX.md`

Protocolos de execução:

- `docs/_canon/_agent/AI_ARCH_EXEC_PROTOCOL.md`
