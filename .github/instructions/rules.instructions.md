---
description:  Mandatory rules for Agent/Copilot every time they are generating code, answering questions, or reviewing changes. These rules are based on agent guards, coding guidelines, and project context defined in the canonical gate scripts and documentation.
applyTo: Hb Track/**

---

Regra prática: **repo não pode ficar “suja” antes de rodar guard/parity/gate**. Então sempre escolha **uma** destas saídas: **reverter** ou **commitar** (e baseline só quando o humano decidir).

## Before any action run:

```powershell
git status --porcelain
```

## After any action run:

```powershell 
git status --porcelain
``` 

## then chose one, below:


### 1) Criei/editei um arquivo sem querer (fora do escopo)

Reverter/apagar na hora:

* Arquivo *modificado*:

```powershell
git restore -- caminho/do/arquivo
```

* Arquivo *novo* (untracked):

```powershell
Remove-Item caminho/do/arquivo
# ou: git clean -n (ver) / git clean -f (apagar) com cuidado
```

### 2) Criei/editei/deleted um arquivo de propósito (faz parte da tarefa)

Não deixe pendente: **commite** com 1 intenção.

```powershell
git add -- caminho/do/arquivo
git commit -m "motivo claro (1 intenção)"
```

Para deletar arquivo versionado:

```powershell
git rm caminho/do/arquivo
git commit -m "chore: remove <arquivo> (motivo)"
```

### 3) Arquivos gerados (`docs/_generated/*`) sujaram após rodar gate/parity

Em geral **não commit** isso (a menos que a tarefa seja atualizar SSOT). Limpe com restore:

No backend root:

```powershell
git restore -- `
  "docs/_generated/alembic_state.txt" `
  "docs/_generated/manifest.json" `
  "docs/_generated/parity_report.json" `
  "docs/_generated/schema.sql"

git restore -- `
  "..\docs\_generated\alembic_state.txt" `
  "..\docs\_generated\manifest.json" `
  "..\docs\_generated\schema.sql" `
  "..\docs\_generated\trd_training_permissions_report.txt"
```

### 4) Checklist “antes de rodar guard/gate”
Sempre rode:

```powershell
git status --porcelain
```

* Se aparecer algo: **reverta ou commite** antes.
* **Não crie** arquivos temporários dentro do repo (use `C:\Temp\`).

### 5) Baseline (guard)

Mesmo com tudo commitado, o guard pode falhar se a baseline não aceitar o novo estado. Então:

* **Commit não substitui baseline**.
* Só faça `agent_guard snapshot` quando você decidir “essa mudança é a nova verdade”.

Regra de ouro: **não deixe o repo sujo**. Sempre escolha uma das 3 opções: **reverter**, **commitar**, ou (em casos específicos) **atualizar baseline**. Nunca deixe arquivos modificados ou não rastreados pendentes após rodar gates/parity. 

## Após o commit, rodar:
```powershell
git status --porcelain
