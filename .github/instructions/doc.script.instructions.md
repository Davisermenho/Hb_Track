---
description: Carregar estas instruções sempre que a tarefa envolver documentar scripts do gate (models_autogen_gate.ps1, parity_gate.ps1, agent_guard.py, model_requirements.py) ou explicar o pipeline SSOT/guard/parity/requirements no Hb Track - Backend.
applyTo: docs/scripts/**, docs/workflows/**, docs/_canon/**, docs/references/exit_codes.md, docs/ADR/_INDEX_ADR.md, Hb Track - Backend/scripts/models_autogen_gate.ps1, Hb Track - Backend/scripts/parity_gate.ps1, Hb Track - Backend/scripts/agent_guard.py, Hb Track - Backend/scripts/model_requirements.py
---

## TAREFA:
Escrever a documentação completa e executável do funcionamento do script **<SCRIPTPATH>** (ex.: `Hb Track - Backend/scripts/models_autogen_gate.ps1`), cobrindo: objetivo, entradas/flags, fluxo passo-a-passo, arquivos gerados/modificados, exit codes, exemplos e troubleshooting.

ESCOPO (NÃO SAIR):
- Documentar APENAS o script alvo e as dependências diretas que ele chama.
- Não “inventar” comportamento: tudo precisa ser ancorado em evidência do repositório (código do script) e em saídas reais quando fornecidas.
- Não alterar código.
- Não atualizar baseline.
- Não criar arquivos temporários no repo.

ARQUIVO DE SAÍDA:
- Criar/atualizar: `docs/workflows/<SCRIPT_NAME>_guide.md` (ex.: `docs/workflows/models_autogen_gate_guide.md`)
- Linguagem: Português
- Estilo: operacional, com comandos copiáveis.

METODOLOGIA (determinística):
1) Ler o conteúdo do script alvo e identificar:
   - parâmetros/flags (`param(...)`)
   - valores padrão
   - dependências (outros scripts/py chamados)
   - etapas numeradas (STEP 1..N) ou blocos (pre-check, autogen, post-check, requirements)
   - regras de decisão (if/else) e mensagens de log
   - propagação de exit codes e casos de catch/throw
2) Extrair a “API do script”:
   - Sintaxe básica
   - Tabela de parâmetros (nome, tipo, obrigatório, default, exemplo)
   - Seções especiais (Allow/AllowCycleWarning/Profile/Create)
3) Descrever o fluxo de execução como “pipeline”:
   - Pré-condições (CWD no backend root, venv, SSOT)
   - Sequência exata de chamadas internas
   - Onde e quando o guard roda
   - Onde e quando o parity roda
   - Onde e quando requirements roda
   - Onde arquivos são gerados/alterados (ex.: `docs/_generated/*`)
4) Documentar exit codes (0/1/2/3/4):
   - significado
   - origem (qual etapa produz)
   - como diagnosticar (qual relatório/trecho de log olhar)
5) Incluir exemplos práticos (copiar/colar), minimamente:
   - Rodar para uma tabela em strict
   - Rodar com allowlist (quando aplicável)
   - Rodar com profile fk + AllowCycleWarning (se o script suportar)
   - Como capturar `$LASTEXITCODE` corretamente (sem pipeline)
6) Troubleshooting orientado a sintomas:
   - Guard exit=3 (drift): como identificar e resolver sem snapshot automático
   - Parity exit=2: como interpretar parity_report
   - Requirements exit=4: como ler requirements_report
   - Crash exit=1: onde procurar traceback/log
   - Artefatos gerados sujando working tree: comando de `git restore` com paths corretos
7) “Do/Don’t” (anti-armadilhas):
   - não criar arquivos temporários no repo
   - não rodar snapshot sem ordem
   - capturar `$LASTEXITCODE` imediatamente
   - não confiar em links do VSCode (`_vscodecontentref_`)

FORMATO OBRIGATÓRIO DA DOCUMENTAÇÃO (estrutura):
1. Visão Geral (o que resolve / quando usar)
2. SSOT e Dependências (arquivos e scripts chamados)
3. Pré-requisitos (checklist com comandos)
4. Interface do Script (parâmetros e exemplos)
5. Fluxo de Execução (passo a passo detalhado)
6. Artefatos Gerados/Modificados (lista e paths)
7. Exit Codes (tabela + diagnóstico por código)
8. Exemplos Completos (copy/paste)
9. Troubleshooting (por sintoma + comandos)
10. FAQ (curta)
11. Changelog do Documento (data/autor)

EVIDÊNCIA (obrigatória no texto):
- Sempre referenciar os nomes reais das funções/etapas/strings de log que existem no script (ex.: `[POST] parity_exit=...`).
- Se algum detalhe não estiver explícito no script, marcar como “Hipótese” e não afirmar como fato.

CONDIÇÃO DE PARADA:
Se você não tiver acesso ao conteúdo do script alvo no contexto atual, PARE e peça o conteúdo do arquivo (ou trecho relevante) antes de escrever a doc.

ENTREGA:
Produzir o markdown completo, pronto para commit, sem placeholders vazios.
