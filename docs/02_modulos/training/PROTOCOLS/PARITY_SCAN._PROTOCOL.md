# Overview

---

**Authority Block**

| Propriedade | Valor |
|---|---|
| Authority | Canon (Canonical Protocol) |
| Scope | training/parity — Validação de alinhamento model ↔ schema |
| Last Verified | 2026-02-08 |
| Depends On | [001-ADR-TRAIN-ssot-precedencia.md](../../../ADR/001-ADR-TRAIN-ssot-precedencia.md), `schema.sql`, `alembic_state.txt` |
| Produces | `parity_report.json`, divergence lists, migration recommendations |

---

**Arquivo:** Hb Track - Backend/scripts/parity_scan.ps1

Este documento descreve o objetivo, pré-requisitos e uso do script de "parity scan" que:

- gera o SSOT/schema via `scripts/generate_docs.py`;
- executa um scan Alembic em modo somente-compare (autogenerate → sem commit automático);
- classifica as diferenças (diffs) usando `scripts/parity_classify.py`;
- opcionalmente falha a execução se forem detectadas diferenças estruturais.

---

## Pré-requisitos

- PowerShell (Windows).
- Repositório clonado em C:\HB TRACK (ou ajustar `-RepoRoot`).
- Virtualenv do projeto com Python e dependências instaladas. O script tenta, na ordem:
  1. `venv\Scripts\python.exe`
  2. `python.exe` (no PATH)
  3. `python` (no PATH)
- Arquivos auxiliares: `scripts/generate_docs.py`, `scripts/parity_classify.py`.
- Infraestrutura Alembic já configurada no backend.
- (Opcional) `scripts/_load_env.ps1` para carregar variáveis de ambiente a partir de `.env`.

---

## O que o script faz (resumo de passos)

1. Executa `scripts/generate_docs.py` para gerar o SSOT/schema.
2. Define a variável de ambiente `ALEMBIC_SCAN_ONLY=1` e, se aplicável, `ALEMBIC_COMPARE_TABLES`.
3. Chama Alembic via Python: `python -m alembic revision --autogenerate -m "<Message>"`, redirecionando a saída para um log.
4. Executa `scripts/parity_classify.py` para transformar o log em `parity_report.json`.
5. Se o flag `-FailOnStructuralDiffs` for passado e `parity_report.json` indicar diffs estruturais, o script sai com código 2. Em falhas críticas sai com código 1; em sucesso sai com código 0.

---

## Parâmetros / Flags

- `-RepoRoot <string>`: caminho absoluto para o root do backend (default: `C:\HB TRACK\Hb Track - Backend`).
- `-Message <string>`: mensagem usada no revision (default: `parity-scan`).
- `-TableFilter <string>`: se fornecido, exporta para `ALEMBIC_COMPARE_TABLES` (ex.: `persons,teams`).
- `-FailOnStructuralDiffs` (switch): se presente, o script verifica `parity_report.json` e sai com erro se houver diffs estruturais.

---

## Arquivos / saídas geradas

- Diretório: `_generated/` (criado se não existir).
- Log Alembic: `_generated/parity-scan.log`.
- Relatório JSON final: `_generated/parity_report.json`.

---

## Códigos de saída

- `0` — sucesso / sem diffs impeditivos.
- `1` — erro crítico (falha em algum dos passos).
- `2` — (quando `-FailOnStructuralDiffs` usado) diffs estruturais detectados.

---

## Como executar — exemplos (PowerShell)

Execução básica (do diretório do script ou com caminho completo):

```powershell
& 'C:\HB TRACK\Hb Track - Backend\scripts\parity_scan.ps1'
```

Especificando `RepoRoot` explicitamente:

```powershell
& 'C:\HB TRACK\Hb Track - Backend\scripts\parity_scan.ps1' -RepoRoot 'C:\HB TRACK\Hb Track - Backend'
```

Com mensagem personalizada e filtro de tabelas:

```powershell
& 'C:\HB TRACK\Hb Track - Backend\scripts\parity_scan.ps1' -Message 'parity-scan-2026-02-06' -TableFilter 'persons,teams'
```

Falhar automaticamente se houver diffs estruturais:

```powershell
& 'C:\HB TRACK\Hb Track - Backend\scripts\parity_scan.ps1' -FailOnStructuralDiffs
```

Observação: se o `venv` não for encontrado, o script tenta o `python` do PATH; melhor prática é ativar o `venv` antes.

---

## Boas práticas antes de rodar

- Ative/valide o `venv` do projeto.
- Verifique que `scripts/generate_docs.py` roda sem erros:

```powershell
python scripts/generate_docs.py
```

- Verifique que `scripts/parity_classify.py` está presente e funcional:

```powershell
python scripts/parity_classify.py --help
```

- Em CI, considere usar `-FailOnStructuralDiffs` para falhar a build quando houver diffs estruturais.

---

## Troubleshooting (problemas comuns)

- Erro: "venv não encontrado" → o script avisará e tentará `python` do PATH. Instale/ative o `venv` ou ajuste `-RepoRoot`.
- Alembic escreve INFO no `stderr`; PowerShell com `ErrorActionPreference=Stop` pode interromper. O script captura a saída e checa `LASTEXITCODE`. Consulte `_generated/parity-scan.log` para detalhes.
- `generate_docs.py` falha: revise dependências e imports; rode isoladamente para ver o traceback.
- `parity_classify.py` não gera `parity_report.json`: verifique parâmetros e o log gerado.
- Saída com código `2`: abra `_generated/parity_report.json` para ver `summary.structural_count` e detalhes dos diffs.

---

## Notas de segurança / permissões

- Não é normalmente necessário executar como administrador; garanta permissão de escrita em `_generated/`.
- Confirme `RepoRoot` antes de rodar para evitar executar em diretório errado.

---

## Checklist rápido antes de executar

- `Python/venv`: ativado e com dependências instaladas.
- `Alembic`: configurado e acessível via Python do `venv`.
- `scripts/generate_docs.py`: roda sem erros.
- `scripts/parity_classify.py`: presente e funcionando.
- Permissão de escrita em `_generated/`.

---
