---
name: models-gate
description: Rodar/avaliar o gate de modelos (Model↔DB) e orientar correção com evidências e critérios de pronto.
argument-hint: "opcional: 'scan', 'fix-next', ou nome da tabela"
---

# Models Gate Protocol

Objetivo: executar ou guiar execução do gate Model↔DB e produzir decisão objetiva (PASS/FAIL) + próxima ação mínima.

## Autoridade e Guias

- [MODELS PIPELINE](../../docs/_canon/05_MODELS_PIPELINE.md)
- [APPROVED COMMANDS](../../docs/_canon/08_APPROVED_COMMANDS.md)
- [TROUBLESHOOTING parity/guard](../../docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md)
- ADR: [013-ADR-MODELS](../../docs/ADR/013-ADR-MODELS.md)

## Evidência Atual

- `docs/_generated/_core/parity_report.json`
- `docs/_generated/_core/schema.sql`
- `docs/_generated/_core/alembic_state.txt`

## Tarefa (Conforme Input)

- **scan**: produzir o passo-a-passo para gerar/atualizar `parity_report.json` e interpretar o resultado
- **fix-next**: escolher a próxima tabela com FAIL (maior impacto) e listar patch mínimo + comandos
- **table**: focar em 1 tabela específica

## Saída Obrigatória

1) **Estado atual do gate** — resumo numérico do `parity_report.json`
2) **Próxima ação recomendada** — com arquivos e diffs esperados
3) **Comandos aprovados para validar** — e critério "pronto suficiente"

**Regra:** Não inventar comandos. Se um comando não estiver em [APPROVED_COMMANDS](../../docs/_canon/08_APPROVED_COMMANDS.md)

