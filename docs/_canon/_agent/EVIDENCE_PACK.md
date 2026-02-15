# EVIDENCE_PACK.md

Status: TEMPLATE / CANONICAL
Version: 1.0.0
Scope: Relatório de execução técnica (Output do Executor)
Applies To: AI Executor (Copilot/Agent) -> AI Architect

---

# 1. TASK IDENTIFICATION

*   **Task ID:** [ID-DA-TASK]
*   **Version:** [V.X.X]
*   **Executor:** [Copilot/Agent Name]
*   **Timestamp Start:** [DD/MM/YYYY HH:MM:SS]
*   **Timestamp End:** [DD/MM/YYYY HH:MM:SS]

---

# 2. EXECUTION SUMMARY

Breve resumo da execução (2 frases).

[RESULTADO: SUCCESS / FAIL / PARTIAL]

---

# 3. COMMAND LOG (RAW OUTPUT)

Lista detalhada de comandos executados e seus respectivos Exit Codes.

| Ordem | Comando PowerShell | Exit Code | Observação |
| :--- | :--- | :--- | :--- |
| 1 | `git status --porcelain` | 0 | Limpo |
| 2 | `powershell -File script.ps1` | 0 | Processo OK |
| ... | ... | ... | ... |

---

# 4. ARTIFACTS MODIFIED

Lista de arquivos alterados (repo-relative; sem `C:/...`).

*   `docs/...`
*   `Hb Track - Backend/...`

---

# 5. GATE VALIDATION EVIDENCE

Provas de que os portões de qualidade passaram.

*   **Portão 1 (Nome):** [COLE O OUTPUT RELEVANTE AQUI]
*   **Portão 2 (Nome):** [COLE O OUTPUT RELEVANTE AQUI]

---

# 6. ACCEPTANCE CRITERIA VERIFICATION

| Critério de Aceite (do Task Brief) | Status | Evidência (Breve nota) |
| :--- | :--- | :--- |
| Critério 1 | [PASS/FAIL] | [Motivo/Prova] |
| Critério 2 | [PASS/FAIL] | [Motivo/Prova] |

---

# 7. INCIDENTS / DEVIATIONS

Se houve alguma falha, erro de permissão ou comportamento inesperado, liste aqui.

*   [Descrição do Desvio 1]
*   [Como foi tratado]

---

# 8. POST-EXECUTION REPO STATUS

Saída final do `git status --porcelain` após limpeza.

```powershell
# [COLE O RESULTADO AQUI]
```

---

# 9. EXECUTOR DECLARATION

"Declaro que a tarefa foi executada seguindo as restrições de escopo do TASK BRIEF e que todas as evidências acima são autênticas."

---

END OF DOCUMENT
