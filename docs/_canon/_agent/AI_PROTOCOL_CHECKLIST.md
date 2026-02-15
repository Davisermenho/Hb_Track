# AI_PROTOCOL_CHECKLIST.md

Status: CANONICAL
Version: 1.0.0
Scope: Pré-validação obrigatória antes da emissão de qualquer TASK BRIEF
Applies To: AI Architect (ChatGPT)

---

# 1. PURPOSE

Este checklist deve ser validado pelo AI Architect antes de emitir qualquer TASK BRIEF.

Objetivo:

* Reduzir falhas de escopo
* Eliminar ambiguidade estrutural
* Garantir determinismo
* Impedir execução fora de contexto
* Minimizar agent drift

Nenhum TASK BRIEF deve ser emitido sem passar por este checklist.

---

# 2. PROBLEM DEFINITION CHECK

[ ] O problema está definido em UMA frase objetiva?
[ ] O objetivo é mensurável?
[ ] Existe critério binário de sucesso (PASS/FAIL)?
[ ] O problema não contém múltiplos objetivos misturados?
[ ] Está claro o estado atual vs estado desejado?

Se qualquer resposta for NÃO → refinar definição antes de continuar.

---

# 3. SSOT VALIDATION CHECK

[ ] O Source of Truth foi explicitamente declarado?
[ ] Existe apenas UM SSOT estrutural?
[ ] O executor não precisará inferir contexto externo?
[ ] O SSOT não está ambíguo ou contraditório?
[ ] O SSOT é estável (não muda durante a execução)?
[ ] Test Plan declarado (arquivos + comandos + asserts mínimos)

Sem Test Plan → Determinism Score máximo = 3/5 → proibido emitir TASK BRIEF.

Se houver múltiplas fontes conflitantes → resolver antes de emitir task.

---

# 4. SCOPE CONTROL CHECK

[ ] READ allowlist está explícita?
[ ] WRITE allowlist está explícita?
[ ] Arquivos proibidos estão declarados?
[ ] O escopo está minimizado ao necessário?
[ ] A task não permite exploração global do repo?

Se o escopo parecer amplo demais → reduzir.

---

# 5. COMMAND VALIDATION CHECK

[ ] Todos os comandos estão listados explicitamente?
[ ] A ordem de execução está definida?
[ ] Cada comando tem efeito verificável?
[ ] O número de comandos está dentro do BUDGET?
[ ] Não existem comandos implícitos?

Nenhum comando implícito é permitido.

---

# 6. ACCEPTANCE CRITERIA CHECK

[ ] Os critérios são objetivos e mensuráveis?
[ ] Existe valor numérico ou condição verificável?
[ ] O exit code esperado está declarado?
[ ] Está claro como validar sucesso sem interpretação subjetiva?
[ ] O sucesso independe de julgamento humano?

Se depender de julgamento subjetivo → reformular.

---

# 7. STOP CONDITION CHECK

[ ] Existem condições explícitas de parada?
[ ] Está claro quando interromper execução?
[ ] Há proteção contra expansão automática de escopo?
[ ] Está definido o que fazer ao falhar?

Sem STOP CONDITIONS → TASK inválida.

---

# 8. ROLLBACK CHECK

[ ] Existe plano de rollback?
[ ] O rollback é executável via comando?
[ ] Está claro o estado esperado após rollback?
[ ] O rollback restaura o estado inicial verificável?

Sem rollback definido → risco estrutural alto.

---

# 9. RISK SURFACE CHECK

[ ] A task altera estrutura de banco?
[ ] A task altera migrations?
[ ] A task altera contratos públicos (API)?
[ ] A task altera invariantes?
[ ] A task altera SSOT?

Se SIM para qualquer item → PRIORITY deve ser HIGH ou CRITICAL.
Avaliar necessidade de ADR antes da execução.

---

# 10. DETERMINISM SCORE

Avaliar de 0 a 5:

0 = Ambíguo
1 = Parcialmente definido
2 = Critérios incompletos
3 = Executável mas amplo
4 = Estruturado e controlado
5 = Totalmente determinístico

Somente emitir TASK BRIEF se score >= 4.

Se score < 4 → refinar especificação.

---

# 11. ARCHITECT DECLARATION (OBRIGATÓRIO)

Antes de emitir TASK BRIEF, declarar explicitamente:

"Checklist validado. Determinism Score: X/5. Task apta para execução."

Sem essa declaração → execução proibida.

---

# 12. FAILURE RESPONSIBILITY RULE

Se o executor falhar por ambiguidade causada por TASK mal definido:

* Responsabilidade é do Architect
* Novo TASK BRIEF deve ser emitido
* Versão da task deve ser incrementada
* O erro deve ser documentado

---

# 13. ENFORCEMENT

Se o Architect ignorar este checklist:

* Task é considerada inválida
* Execução deve ser bloqueada
* Nova versão deve ser emitida

Este documento é obrigatório antes de qualquer emissão de TASK BRIEF no HB Track.

---

END OF DOCUMENT
