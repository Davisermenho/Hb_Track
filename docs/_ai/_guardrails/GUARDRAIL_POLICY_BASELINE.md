# GUARDRAIL_POLICY_BASELINE.md

> **Parent:** [`GUARDRAILS_INDEX.md`](GUARDRAILS_INDEX.md) (Entry point único para todos os guardrails)  
> **Domain:** Baseline Policy (.hb_guard/baseline.json — LOCAL only)  
> **Version:** 1.0.0  
> **Last Updated:** 2026-02-13

## Descrição
Guardrail crítico: baseline.json é LOCAL, NUNCA committed. Contém política, evidência, recovery paths.

---

## Política: Baseline é Local

### Declaração
**.hb_guard/baseline.json** é um artefato de **SESSÃO LOCAL**, gerado por `agent_guard.py snapshot baseline` e **NUNCA commitado** ao repositório.

### Evidência
- `.gitignore:141` contém `.hb_guard/` (deliberado)
- Canon docs (5 files) documentam "Baseline é LOCAL"
- Commit `314502b` ("chore(canon): align-baseline-local-never-committed") registra essa decisão

### Razão Design
- Baseline detecta mudanças do agente durante uma **sessão**
- Não deve persistir entre sessões (cada sessão = novo contexto)
- Git tracking prejudicaria trilha de versão (commits poluidores)

---

## Comportamento Esperado

### Antes de Executar Gates
1. `agent_guard.py snapshot baseline` cria `.hb_guard/baseline.json` (LOCAL)
2. Guard runs, parity runs, requirements run → todos validated
3. Baseline fica em `.hb_guard/` para a sessão
4. **NUNCA** `git add .hb_guard/baseline.json`

### Após Sessão Terminar
1. Baseline persiste em `.hb_guard/baseline.json` (local, não tracked)
2. Próxima sessão: novo `agent_guard.py snapshot baseline` (sobrescreve)
3. Histórico de baselines não é mantido (por design)

### Se Commitado Acidentalmente
1. `git restore .hb_guard/baseline.json` (remover do index)
2. Verificar `.gitignore` (deve incluir `.hb_guard/`)
3. `git commit --amend` para remover do commit anterior (se não pushado)

---

## Checklist: Validação

- [ ] `.gitignore` contém `.hb_guard/`
- [ ] `git status --porcelain | grep baseline.json` retorna vazio
- [ ] Baseline.json existe em `.hb_guard/` (local, não staged)
- [ ] Nenhum commit recente tem baseline.json modificado
- [ ] Docs canônicos menciona "Baseline é LOCAL"

---

## Recovery Paths

### Cenário 1: `git add .hb_guard/baseline.json` acidentalmente
```powershell
git restore --staged .hb_guard/baseline.json
git restore .hb_guard/baseline.json  # (opcional, se quiser reset)
git status --porcelain  # Verifyit's removed
```

### Cenário 2: Baseline.json está em commit não-pushed
```powershell
git revert HEAD  # ou
git reset --soft HEAD~1  # (volta, mantém mudanças staged)
git restore --staged .hb_guard/baseline.json
git commit -m "..."
```

### Cenário 3: Baseline.json está em commit já pushed
```powershell
# Não reverta commit (pode quebrar trilha). Em vez disso:
# 1. Avisar ao time
# 2. Adicionar .gitignore entry (se não houver)
# 3. Em PR seguinte: remover arquivo com "git rm --cached"
# 4. Mencionar em EXECUTIONLOG
```

---

## TODO
- [ ] Criar pre-commit hook para detectar baseline.json
- [ ] Documentar como restaurar baseline corrompido
- [ ] Adicionar alert se baseline mais antigo que 24h
