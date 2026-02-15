---
description: Carregar para qualquer tarefa no repositório HB Track. Sempre iniciar pela documentação canônica (00_START_HERE.md) e respeitar SSOT/Authority.
applyTo: "**"
---

Regras globais:
- Load `docs/_canon/AI_KERNEL.md` before answering. (OBRIGATÓRIO)
- Porta única: ler primeiro `docs/_canon/00_START_HERE.md` para entender a organização documental e os próximos passos recomendados.
- Se precisar de contexto operacional de agente, usar `docs/_ai/_INDEX.md` (stub redirect) apenas como ponte para o canônico.
- Follow `./docs/_canon/LANGUAGE_PROTOCOL.md` strictly. (OBRIGATÓRIO)
- Before generating any ARCH_REQUEST: Load and comply with `docs/_canon/ARCH_REQUEST_GENERATION_PROTOCOL.md` (OBRIGATÓRIO)
- Agent roles are defined in `docs/_canon/_agent/AGENT_ROLE_MATRIX.md`. Agents MUST respect role boundaries. (OBRIGATÓRIO)
- Use governance tooling before commits: `python docs/scripts/_ia/ai_governance_linter.py` (RECOMENDADO)
- SSOT estrutural de DB: `Hb Track - Backend/docs/_generated/schema.sql` (gerado por `scripts/inv.ps1 refresh`).
- Não inventar: decisões devem citar paths/outputs reais.
- Não criar arquivos temporários/backups dentro do repo.
- Capturar `$LASTEXITCODE` imediatamente após comandos (sem pipeline antes).
- Antes de criar snapshots, obter autorização (para evitar poluição de histórico).
- Antes de alterar arquivos, verificar se há mudanças não commitadas (para evitar conflitos).
- Antes de corrigir erros, entender a causa raiz (para evitar correções superficiais).
- Antes de adicionar dependências, avaliar o impacto (para evitar bloat).
- Ao revisar código, focar em legibilidade e manutenibilidade (para evitar dívidas técnicas).
- Antes de remover código, verificar se há referências (para evitar quebras).
- Antes de adicionar código, considerar a simplicidade (para evitar complexidade desnecessária).
- Antes de alterar a estrutura do projeto, avaliar a consistência (para evitar confusão).
- Antes de alterar a configuração, entender o contexto (para evitar efeitos colaterais).
- Após identificar a causa de um problema, apresentar a solução e pedir confirmação antes de implementar (para evitar mudanças indesejadas).

Regras críticas: CWD, stop-on-first-failure, sem temporários, capturar $LASTEXITCODE, snapshot só com autorização.

# SEMPRE LER E SEGUIR AS DOCUMENTAÇÕES CANÔNICAS RELACIONADAS ANTES DE QUALQUER AÇÃO.
C:\HB TRACK\docs\_canon\_agent\AGENT_DRIFT_RULES.md
C:\HB TRACK\docs\_canon\_agent\AGENT_ROLE_MATRIX.md
C:\HB TRACK\docs\_canon\_agent\AI_ARCH_EXEC_PROTOCOL.md
C:\HB TRACK\docs\_canon\_agent\AI_INCIDENT_RESPONSE_POLICY.md
C:\HB TRACK\docs\_canon\_agent\AI_PROTOCOL_CHECKLIST.md
C:\HB TRACK\docs\_canon\_agent\AI_TASK_VERSIONING_POLICY.md
C:\HB TRACK\docs\_canon\_agent\EVIDENCE_PACK.md
C:\HB TRACK\docs\_canon\_agent\GOVERNANCE_AUDIT_REPORT.md
C:\HB TRACK\docs\_canon\_agent\SCRIPTS_classification.md
C:\HB TRACK\docs\_canon\_agent\TASK_BRIEF.md
C:\HB TRACK\docs\_canon\_agent\WHEN_TO_USE_TASK_BRIEF.md
