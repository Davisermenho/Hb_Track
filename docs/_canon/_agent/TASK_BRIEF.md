# TASK_BRIEF.md

Status: TEMPLATE / CANONICAL
Version: 1.0.0
Scope: Instrução de execução (Input do Architect -> Executor)
Applies To: AI Architect -> AI Executor

---

# 1. TASK OVERVIEW

*   **Task ID:** [TASK-ID-XXXX]
*   **Title:** [Nome Curto da Tarefa]
*   **Version:** [Incrementar conforme re-emissões]
*   **Priority:** [LOW | MEDIUM | HIGH | CRITICAL]
*   **Budget:** [MAX_COMMANDS] / [MAX_TIME]

---

# 2. CONTEXT & SSOT

*   **Problema:** [O que precisa ser resolvido?]
*   **Objetivo Final:** [Qual o estado desejado?]
*   **SSOT (Authority):** [Ponto central de verdade: schema.sql, OpenAPI, ADR, etc.]

---

# 3. SCOPE (ALLOWLIST)

*   **Read Access:** [Lista de diretórios/arquivos]
*   **Write Access:** [Lista de diretórios/arquivos]
*   **Prohibited:** [O que NÃO tocar em hipótese alguma]

---

# 4. EXECUTION PLAN (STEP-BY-STEP)

Roteiro obrigatório de execução.

1.  **Preflight:** (Ex: `git status`, validar venv)
2.  **Action 1:** [Comando/Ação]
3.  **Action 2:** [Comando/Ação]
4.  **Verification:** [Comando de gate/teste]
5.  **Cleanup:** [Remover arquivos temporários]

---

# 5. ACCEPTANCE CRITERIA (BINARY)

Somente critérios do tipo Sim/Não.

*   [ ] O comando X retorna EXIT 0.
*   [ ] O arquivo Y contém a string Z.
*   [ ] O gate de paridade está PASS.
*   [ ] Repo está clean (`git status` vazio exceto mods esperadas).

---

# 6. STOP CONDITIONS (CRITICAL)

Condições de interrupção imediata.

1.  **ERRO NO COMANDO X:** Se EXIT != 0, pare.
2.  **AGENT DRIFT:** Se você perceber que está saindo do escopo de escrita.
3.  **CONFLITO SSOT:** Se o código contradizer o schema.sql.

---

# 7. ROLLBACK PLAN

O que fazer se tudo der errado.

*   Comando: [Ex: `git restore .`]
*   Estado esperado: [Ex: Clean main branch]

---

# 8. TEST PLAN (OBRIGATÓRIO)

**TEST_PLAN**:
  1. TEST_FILES_REQUIRED: lista exata
  2. TEST_COMMANDS: comandos exatos
  3. MIN_ASSERTS: bullet com 3–5 asserts que precisam existir
**ACCEPTANCE**:
   pytest exit 0
   collected > 0
**EVIDENCE_PACK**:
   pytest_output.txt

---

# 9. ARCHITECT AUTHORIZATION

"Checklist validado. Determinism Score: X/5. Task apta para execução."

---

END OF DOCUMENT
