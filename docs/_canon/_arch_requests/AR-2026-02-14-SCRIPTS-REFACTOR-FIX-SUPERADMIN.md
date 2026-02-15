# ARCH_REQUEST — REFATORAÇÃO IDEMPOTÊNCIA FIX_SUPERADMIN

Status: APPROVED_FOR_EXECUTION
Version: 1.0.0
Task ID: AR-2026-02-14-SCRIPTS-REFACTOR-FIX-SUPERADMIN
Priority: HIGH
Budget: MAX_COMMANDS=30 / MAX_TIME=180min
Depends On: AR-2026-02-13-SCRIPTS-DOCS-AUDIT (COMPLETE_PASS)

---

## 1) CONTEXTO

Problema: `Hb Track - Backend/scripts/fix_superadmin.py` classificado como `DIVIDA_TECNICA` por falta de prova de idempotência (AUDIT_SCRIPTS_DOCS_REPORT.md seção 4.3).

Objetivo Final: Refatorar script para nível Enterprise conforme contrato SCRIPTS_GUIDE.md, implementando:
- Idempotência verificável (execução dupla = noop)
- JSON logging estruturado
- Interface CLI padrão (--dry-run)

---

## 2) OBJETIVOS (MUST)

- MUST-01: Implementar idempotência via state checking (DB logic check).
- MUST-02: Adicionar JSON logging estruturado (timestamp, operation, status, changes).
- MUST-03: Implementar flag `--dry-run` (preview sem aplicar mudanças).
- MUST-04: Smoke test de idempotência (executar 2x → 2ª run = noop).
- MUST-05: Atualizar SCRIPTS_GUIDE.md (DIVIDA_TECNICA → INCORPORAR).

---

## 3) SSOT / AUTORIDADE

- `docs/_canon/SCRIPTS_GUIDE.md` (contrato Enterprise)
- `docs/_canon/AI_KERNEL.md` (governança)
- `docs/_canon/_arch_requests/AUDIT_SCRIPTS_DOCS_REPORT.md` (classificação atual)
- `Hb Track - Backend/scripts/fix_superadmin.py` (código atual)
- `Hb Track - Backend/app/models/user.py` (model de referência)

---

## 4) SCOPE (ALLOWLIST)

### Read Access
- `Hb Track - Backend/scripts/fix_superadmin.py`
- `Hb Track - Backend/app/models/user.py`
- `Hb Track - Backend/app/core/security.py`
- `docs/_canon/SCRIPTS_GUIDE.md`
- `docs/_canon/_arch_requests/AUDIT_SCRIPTS_DOCS_REPORT.md`

### Write Access
- `Hb Track - Backend/scripts/fix_superadmin.py` (refatoração)
- `docs/_canon/SCRIPTS_GUIDE.md` (atualizar classificação)
- `docs/_canon/_arch_requests/AR-2026-02-14-SCRIPTS-REFACTOR-FIX-SUPERADMIN.md` (este doc)
- `docs/_canon/_arch_requests/VALIDATION_MUST_REPORT_AR-2026-02-14.md` (validação)

### Proibido
- Modificar models (`app/models/user.py`)
- Modificar schema (`db/alembic/versions/*`)
- Criar arquivos temporários no repo
- Executar comandos destrutivos sem --dry-run

---

## 5) DELTA ESTRUTURAL

### Modificações no Script

**Estado Atual (fix_superadmin.py)**:
```python
# Script sem state checking
# Sempre tenta criar/atualizar superadmin
# Sem logs estruturados
# Sem --dry-run
```

**Estado Alvo**:
```python
# 1. Pre-flight: verificar se superadmin já existe e está correto
# 2. State check: comparar password hash, permissions, tenant_id
# 3. Decision:
#    - Se correto: skip (return 0, log "noop")
#    - Se missing: create (return 1, log "created")
#    - Se incorrect: update (return 2, log "updated")
# 4. JSON logging: {timestamp, operation, user_id, status, changes}
# 5. --dry-run: preview changes sem aplicar
```

### Atualização Documental

**SCRIPTS_GUIDE.md seção 7**:
```diff
- 8. `Hb Track - Backend/scripts/model_requirements.py` — requirements validation
+ 8. `Hb Track - Backend/scripts/fix_superadmin.py` — idempotent superadmin fix
+ 9. `Hb Track - Backend/scripts/model_requirements.py` — requirements validation
```

**SCRIPTS_GUIDE.md seção 8 (Classificação)**:
```diff
- fix_*.py → DIVIDA_TECNICA (sem prova de idempotência)
+ fix_superadmin.py → INCORPORAR (idempotência comprovada via smoke tests)
```

---

## 6) EXECUTION PLAN

### Phase 1: Análise do Estado Atual
1. Ler `fix_superadmin.py` atual
2. Identificar lógica de criação/atualização
3. Mapear dependências (models, security)

### Phase 2: Implementação de Idempotência
1. Adicionar função `check_superadmin_state()`
   - Query DB: superadmin user exists?
   - Verify: password hash matches?
   - Verify: permissions correct?
2. Modificar lógica principal:
   - If state correct: skip (return 0)
   - If user missing: create (return 1)
   - If user incorrect: update (return 2)
3. Adicionar tratamento de erros com exit codes específicos

### Phase 3: JSON Logging
1. Definir estrutura de log:
   ```json
   {
     "timestamp": "2026-02-14T10:00:00-03:00",
     "script": "fix_superadmin.py",
     "operation": "check|create|update|skip",
     "user_id": 123,
     "status": "success|error",
     "changes": {"password": false, "permissions": false},
     "dry_run": false
   }
   ```
2. Implementar logging em pontos-chave:
   - Pre-flight check
   - State decision
   - DB operations (se não --dry-run)
   - Error handling

### Phase 4: CLI Interface
1. Adicionar argparse:
   - `--dry-run`: preview sem aplicar
   - `--output`: json|text (default: text)
   - `--tenant-id`: (opcional, default: global)
   - `--help`: usage + examples
2. Validar flags com smoke tests

### Phase 5: Smoke Tests
1. Test 1: Fresh DB → run → user created (exit 1)
2. Test 2: Run again → noop (exit 0) ✅ IDEMPOTÊNCIA
3. Test 3: Delete user → run → recreate (exit 1)
4. Test 4: Change password → run → detect & update (exit 2)
5. Test 5: `--dry-run` → preview sem aplicar (exit 0)

### Phase 6: Documentação
1. Atualizar SCRIPTS_GUIDE.md (classificação)
2. Criar VALIDATION_MUST_REPORT (evidências de smoke tests)
3. Commit com mensagem canônica

---

## 7) GATES

- **GATE-A (Idempotência)**: Execução dupla resulta em status "noop" (exit 0) na 2ª run
- **GATE-B (JSON Logging)**: Logs parseáveis via `ConvertFrom-Json` (PowerShell) ou `json.loads()` (Python)
- **GATE-C (--dry-run)**: Flag funcional sem side effects no DB
- **GATE-D (CLI Standard)**: `--help` retorna usage; flags obrigatórios implementados
- **GATE-E (Documentation)**: SCRIPTS_GUIDE.md atualizado; classificação mudou de DIVIDA → INCORPORAR

---

## 8) ACCEPTANCE CRITERIA (BINARY)

- [ ] MUST-01: State checking implementado (check before create/update)
- [ ] MUST-02: JSON logging estruturado em todos os operations
- [ ] MUST-03: `--dry-run` flag funcional
- [ ] MUST-04: Smoke test de idempotência: 2ª execução = noop (exit 0)
- [ ] MUST-05: SCRIPTS_GUIDE.md atualizado (seção 7 + 8)
- [ ] Código segue padrões Python (type hints, docstrings)
- [ ] Exit codes documentados (0=noop, 1=created, 2=updated, 3=error)
- [ ] Help message completo com exemplos

---

## 9) STOP CONDITIONS

- Script modificado sem preservar compatibilidade com uso atual
- State checking requer mudanças no model User (fora de escopo)
- Smoke tests falhando por >2 tentativas (design error)
- --dry-run com side effects detectados

---

## 10) ROLLBACK PLAN

- `git restore -- Hb Track - Backend/scripts/fix_superadmin.py`
- `git restore -- docs/_canon/SCRIPTS_GUIDE.md`
- Reverter commit se já commitado
- Documentar failure em VALIDATION_MUST_REPORT

---

## 11) TEST PLAN

### TEST_FILES_REQUIRED
- `Hb Track - Backend/scripts/fix_superadmin.py` (refatorado)
- `docs/_canon/SCRIPTS_GUIDE.md` (atualizado)
- `docs/_canon/_arch_requests/VALIDATION_MUST_REPORT_AR-2026-02-14.md` (novo)

### MIN_ASSERTS
- assert: `python fix_superadmin.py` (1ª run) → exit 1 ou 2
- assert: `python fix_superadmin.py` (2ª run) → exit 0 (noop)
- assert: `python fix_superadmin.py --dry-run` → exit 0, sem DB changes
- assert: `python fix_superadmin.py --help` → usage message
- assert: JSON log parseable via `json.loads()`

---

## 12) ARCHITECT AUTHORIZATION

Determinism Score: 5/5
- [x] Script target bem definido
- [x] State tracking strategy clara (db logic check)
- [x] Acceptance criteria binários
- [x] Smoke tests específicos
- [x] Rollback plan trivial

Task apta para execução.

---

## EXECUTION METRICS (Target)

```yaml
ESTIMATED_EFFORT:
  analysis: 15min
  implementation: 90-120min
  testing: 30-45min
  documentation: 15min
  total: 150-180min (within budget)
  
COMMANDS_ESTIMATE: 20-25/30
```
