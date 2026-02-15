---
description: "PowerShell Command Policy: allowlist, quoting, CWD, e confirmação de segurança. Carregar sempre que for rodar comandos no terminal para evitar erros e riscos de segurança."
applyTo: "**"
---

REGRAS (OBRIGATÓRIAS):
1) Só sugerir comandos que existam em docs/_canon/08_APPROVED_COMMANDS.md.
2) Se precisar de um comando novo: pedir aprovação explícita e, APÓS aprovado, registrar no 08_APPROVED_COMMANDS.md.
3) Sempre emitir comandos em bloco ```powershell``` e SEM placeholders ambíguos.
4) Sempre prefixar com um “preflight” mínimo (pwd + git root + git status).
5) Em paths com espaço, sempre usar aspas e/ou caminhos relativos ao repo root.
6) Proibido: Invoke-Expression/iex, baixar e executar script remoto, Remove-Item destrutivo, git reset --hard, git clean -fd (sem aprovação explícita).

--- 

Regras adicionais (CWD / quoting / segurança):
- Para comandos operacionais do HB Track, preferir `powershell.exe` e a forma wrapper canônica descrita em `docs/_canon/00_START_HERE.md`.
- Validar CWD antes de executar (repo root vs backend root, conforme o comando).
- Proibido usar utilitários POSIX em PowerShell (ex.: `grep/sed/awk/find/xargs`); usar equivalentes PowerShell quando aplicável.
- Após executar comando externo: capturar `$LASTEXITCODE` imediatamente (não usar pipeline antes da captura).
