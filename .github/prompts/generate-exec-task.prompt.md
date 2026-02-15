---
name: generate-exec-task
description: Gerar um EXEC_TASK a partir de ADR/SSOT seguindo template e incluindo gates, evidências e checklist de PR.
argument-hint: "obrigatório: ADR alvo (ex: ADR-MODELS-001 ou caminho do arquivo)"
---

# Generate Exec Task Protocol

Objetivo: criar/atualizar um documento de execução (EXEC_TASK) derivado de uma ADR, com passos reproduzíveis e critérios de aceitação.

## Fontes

- Template: [INV_TASK_TEMPLATE](../../docs/_ai/INV_TASK_TEMPLATE.md)
- Workflows canônicos: [WORKFLOWS](../../docs/_canon/03_WORKFLOWS.md)
- Approved commands: [APPROVED_COMMANDS](../../docs/_canon/08_APPROVED_COMMANDS.md)
- ADR Models: [013-ADR-MODELS](../../docs/ADR/013-ADR-MODELS.md)
- Pasta de execução: `docs/execution_tasks/`

## Entrada

ADR alvo informado em `${input:adr}` 

Exemplos: `"docs/ADR/013-ADR-MODELS.md"` ou um identificador equivalente

## Tarefa

1) **Localize e leia a ADR alvo** no workspace (não usar memória)

2) **Derive o EXEC_TASK** (60% copia estruturada da decisão + 40% detalhes executáveis):
   - Pré-requisitos
   - Passos numerados
   - Gates/validações e evidências (comandos aprovados)
   - Condições de abort
   - Checklist de PR e atualização de logs (CHANGELOG/EXECUTIONLOG se aplicável)

3) **Salve** com nome consistente em `docs/execution_tasks/` e atualize índices/logs relevantes

## Saída

- Estrutura final do arquivo (títulos/seções)
- Lista de arquivos tocados
- Critérios de aceitação e evidências

**Regra:** Use apenas comandos de [APPROVED_COMMANDS](../../docs/_canon/08_APPROVED_COMMANDS.md). Se precisar de novo comando, documente em ADR ou marque como PENDENTE.
