---
name: parity-fix
description: Corrigir divergências Model↔DB guiado por parity_report.json, schema.sql e ADR-MODELS. Produz plano + patch + evidências.
argument-hint: "opcional: nome da tabela alvo (ex: categories) ou 'next'"
---

# Parity Fix Protocol

Objetivo: reduzir divergências estruturais Model↔DB com base em evidência do workspace. Não inferir. Sempre citar arquivos e trechos consultados.

## Contexto Canônico (Leia/Consulte)

- [START HERE](../../docs/_canon/00_START_HERE.md)
- [AUTHORITY/SSOT](../../docs/_canon/01_AUTHORITY_SSOT.md)
- [MODELS PIPELINE](../../docs/_canon/05_MODELS_PIPELINE.md)
- [TROUBLESHOOTING parity/guard](../../docs/_canon/09_TROUBLESHOOTING_GUARD_PARITY.md)
- ADR: [013-ADR-MODELS](../../docs/ADR/013-ADR-MODELS.md)

## Evidência Obrigatória (Use Sempre)

- parity report: `Hb Track - Backend/docs/_generated/_core/parity_report.json`
- schema: `Hb Track - Backend/docs/_generated/_core/schema.sql`
- alembic state: `Hb Track - Backend/docs/_generated/_core/alembic_state.txt`

## Tarefa

1) **Identifique o alvo:**
   - Se `${input:table}` = 'next' ou vazio, selecione a próxima divergência de maior impacto no `parity_report.json`
   - Caso um nome de tabela seja fornecido, filtre o `parity_report.json` para essa tabela

2) **Extraia a especificação real do DB** para o alvo a partir de `schema.sql`:
   - colunas, tipos, nullability, defaults, constraints, PK/FK, índices relevantes

3) **Localize o(s) model(s) SQLAlchemy correspondente(s)** no codebase e compare item-a-item com o DB

4) **Proponha o patch mínimo** (1 tabela por vez), mantendo precedência/SSOT do projeto

5) **Defina o comando exato para revalidar** (use apenas comandos aprovados em [APPROVED_COMMANDS](../../docs/_canon/08_APPROVED_COMMANDS.md)). Inclua o output esperado (ex.: `structural_count` diminui)

## Entrega

Responda em 3 blocos:

A) **Diagnóstico** — com citações de arquivos e trechos/linhas relevantes  
B) **Patch Sugerido** — arquivos a alterar + mudança objetiva  
C) **Evidência/Validação** — comandos e critérios de sucesso

Se faltar evidência (arquivo não existe / path mudou), declare **PENDENTE: …** e diga o comando para gerar.
