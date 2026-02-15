# INVARIANTS_TRAINING.md — Invariantes do Módulo TRAINING (HB Track)

---

**Authority Block**

| Propriedade | Valor |
|---|---|
| Authority | SSOT (Single Source of Truth) |
| Scope | training/invariants — Catálogo de Invariantes |
| Last Verified | 2026-02-08 |
| Depends On | [001-ADR-TRAIN-ssot-precedencia.md](../../../ADR/001-ADR-TRAIN-ssot-precedencia.md), `schema.sql`, `openapi.json` |
| Produces | Test cases, migration strategies, enforcement rules |

---

## Change control

* **Válido para**: commit `e02c83ef`
* **Fonte canônica**: `TRD_TRAINING.md` v1.8 (Generated at: `2026-01-29T10:05:54Z`)
* **Última atualização**: 2026-02-08 (adicionadas INV-TRAIN-047 a INV-TRAIN-051)
* **Fontes de verdade**:

  * `Hb Track - Backend/docs/_generated/openapi.json`
  * `schema.sql`
  * `docs/_generated/alembic_state.txt`
  * `docs/_generated/manifest.json`
* **Precedência**: `DB constraints > service validations > OpenAPI > docs manuais`

## Convenções

* **Confirmada**: existe evidência objetiva (constraint nomeada / file:line / router + service).
* **Pretendida**: comportamento descrito como regra, mas **não há evidência localizada** no código/schema (ainda).
* **Inativa**: implementação existe, mas está **comentada/flagada/desligada** (há evidência disso).

Formato de cada item:

* **ID**
* **Status**
* **Enunciado**
* **Status**
* **Escopo**
* **Onde é imposto**
* **Evidência**
* **Status/Teste** (quando revisado)

## Blocos SPEC (Machine-Parseable Contract)

Cada INV CONFIRMADA possui um bloco **SPEC** (spec_version: "1.0") que define o contrato normativo parseável por `verify_invariants_tests.py`. Este bloco elimina ambiguidades de interpretação e permite validação binária (PASS/FAIL) da conformidade dos testes.

### Estrutura do bloco SPEC

```yaml
spec_version: "1.0"
id: "INV-TRAIN-XXX"
status: "CONFIRMADA"
test_required: true  # ou false para aliases

units:  # Lista de enforcement points (DB, service, API, etc.)
  - unit_key: "descriptive-key"  # identificador único do unit
    class: "A|B|C1|C2|D|E1|E2|F"  # classe de enforcement (DoD)
    required: true  # se false, unit é opcional/suplementar
    description: "Brief description"
    anchors:  # Namespace hierárquico para evidências
      db.table: "table_name"
      db.constraint: "constraint_name"
      db.sqlstate: "23514"  # ou 23505 para UNIQUE
      code.file: "path/to/file.py"
      code.function: "function_name"
      api.operation_id: "operation_id"
      celery.task: "task_name"

tests:
  primary: "tests/path/to/test_file.py"  # arquivo principal
  node: "TestInvTrainXXX"  # classe de teste esperada
  coverage: [...]  # opcional: métodos de teste esperados

# Para aliases (INV duplicada que referencia canonical):
canonical_id: "INV-TRAIN-YYY"  # ID da INV canônica
alias_type: "subset|equivalent"  # tipo de aliasing
legacy_reason: "Brief reason for duplicate"
```

### Padrões de migração implementados

#### 1. Single-unit pattern (maioria dos INVs)

Um enforcement point único (DB constraint, service validation, etc.):

```yaml
units:
  - unit_key: "main"
    class: "A"
    description: "Descrição da regra"
    anchors:
      db.table: "table_name"
      db.constraint: "constraint_name"
```

**Exemplos**: INV-009, INV-010, INV-030, INV-032, INV-033, INV-034, INV-035, INV-036, INV-037

#### 2. Multi-unit pattern (enforcement em múltiplas camadas)

Múltiplos enforcement points para a mesma regra (ex: DB column + service validation):

```yaml
units:
  - unit_key: "db-column"
    class: "B"
    required: true
    description: "Database column locked_at documents the rule"
    anchors:
      db.table: "wellness_pre"
      db.column: "locked_at"
  
  - unit_key: "service-validation"
    class: "C2"
    required: true
    description: "Service enforces 2-hour deadline"
    anchors:
      code.file: "app/services/wellness_pre_service.py"
      code.function: "validate_deadline"
```

**Exemplos**: INV-002, INV-003 (DB column B + service validation C2)

#### 3. Multi-table pattern (constraint uniforme em várias tabelas)

Uma constraint pattern aplicada em múltiplas tabelas (enforcement único, múltiplas evidências):

```yaml
units:
  - unit_key: "db-constraint-multi-table"
    class: "A"
    required: true
    description: "CHECK constraint pattern across multiple tables"
    anchors:
      db.pattern: "deleted_at and deleted_reason must both be NULL or both be NOT NULL"
      db.sqlstate: "23514"
      db.constraints:
        - name: "ck_training_sessions_deleted_reason"
          table: "training_sessions"
          schema_line: 2634
        - name: "ck_wellness_pre_deleted_reason"
          table: "wellness_pre"
          schema_line: 2890
```

**Exemplo**: INV-008 (soft delete reason pair em 4 tabelas)

#### 4. Multi-constraint pattern (várias constraints para mesma regra)

Uma regra com múltiplas constraints relacionadas (ex: trigger + função + CHECKs):

```yaml
units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Derivação automática de phase_focus"
    anchors:
      db.table: "training_sessions"
      db.trigger: "tr_derive_phase_focus"
      db.function: "fn_derive_phase_focus"
      db.constraints:
        - "ck_phase_focus_attack_consistency"
        - "ck_phase_focus_defense_consistency"
        - "ck_phase_focus_transition_defense_consistency"
        - "ck_phase_focus_transition_offense_consistency"
```

**Exemplo**: INV-031 (trigger + função + 4 CHECKs)

#### 5. Alias pattern (INV duplicada referencia canonical)

Para INVs que compartilham enforcement (ex: INV-028 = subset de INV-001):

```yaml
spec_version: "1.0"
id: "INV-TRAIN-028"
status: "CONFIRMADA"
test_required: false  # Não requer teste separado
canonical_id: "INV-TRAIN-001"  # Referencia INV canônica
alias_type: "subset"
legacy_reason: "Same constraint ck_training_sessions_focus_total_sum"

units:
  - unit_key: "reference-to-canonical"
    class: "A"
    required: false
    description: "References INV-TRAIN-001 unit 'db-constraint-training-sessions'"
    anchors:
      db.table: "training_sessions"
      db.constraint: "ck_training_sessions_focus_total_sum"

tests:
  primary: "tests/training/invariants/test_inv_train_001_focus_sum_constraint.py"
  note: "Covered by canonical INV-TRAIN-001 test"
```

**Exemplo**: INV-028 (alias de INV-001)

### Validação dos blocos SPEC

Execute `docs/scripts/verify_invariants_tests.py` para validar:

1. **Parsing SPEC**: todos os blocos YAML são válidos
2. **Aliases**: `canonical_id` aponta para INV existente, não duplica testes
3. **Coverage 1:1**: cada INV tem exatamente 1 test file principal
4. **DoD-0 através DoD-9**: conformidade com Definition of Done
5. **Obrigação A/B**: docstrings dos testes contêm anchors e evidências

```bash
# Validação completa (strict mode, exit code 2 se violations)
python docs/scripts/verify_invariants_tests.py

# Com report em arquivo
python docs/scripts/verify_invariants_tests.py --report-txt report.txt

# Validação parcial (apenas coverage + DoD-0)
python docs/scripts/verify_invariants_tests.py --validation-level basic
```

**Status da migração**: 36/36 INVs confirmadas migradas com blocos SPEC (100%) ✅

---

## 1) Confirmadas

### INV-TRAIN-001 — Soma de focos ≤ 120%

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-001"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "db-constraint-training-sessions"
    class: "A"
    required: true
    description: "CHECK constraint on training_sessions table"
    anchors:
      db.table: "training_sessions"
      db.constraint: "ck_training_sessions_focus_total_sum"
      db.sqlstate: "23514"
      db.columns: ["focus_physical", "focus_technical", "focus_tactical", "focus_psychological"]
  
  - unit_key: "db-constraint-session-templates"
    class: "A"
    required: true
    description: "CHECK constraint on session_templates table"
    anchors:
      db.table: "session_templates"
      db.constraint: "chk_session_templates_total_focus"
      db.sqlstate: "23514"
      db.columns: ["focus_physical", "focus_technical", "focus_tactical", "focus_psychological"]

tests:
  primary: "tests/training/invariants/test_inv_train_001_focus_sum_constraint.py"
  node: "TestInvTrain001FocusSumConstraint"
  coverage:
    - "test_valid_case__sum_at_120"
    - "test_invalid_case_1__sum_exceeds_120"
    - "test_invalid_case_2__negative_focus"
```

* **Status**: CONFIRMADA
* **Escopo**: `session_templates`, `training_sessions`, `training_microcycles`
* **Onde é imposto**: DB constraints + service
* **Evidência**:
  * `chk_session_templates_total_focus` (`schema.sql:2127`)
  * `ck_training_sessions_focus_total_sum` (`schema.sql:2640`)
  * `Hb Track - Backend/app/services/training_microcycle_service.py:11` (regra documentada)
* **Teste**: `tests/integration/test_inv_train_001_focus_sum_constraint.py::TestInvTrain001FocusSumConstraint::test_focus_sum_at_limit_120_accepted`; `tests/integration/test_inv_train_001_focus_sum_constraint.py::TestInvTrain001FocusSumConstraint::test_focus_sum_exceeds_120_rejected`

### INV-TRAIN-002 — Deadline Wellness Pré (até 2h antes da sessão)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-002"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "db-column"
    class: "B"
    required: false
    description: "Database column locked_at documents the rule"
    anchors:
      db.table: "wellness_pre"
      db.column: "locked_at"
      db.comment: "pré editável até 2h antes da sessão"
  
  - unit_key: "service-validation"
    class: "C2"
    required: true
    description: "Service enforces 2h deadline with ValidationError"
    anchors:
      code.file: "app/services/wellness_pre_service.py"
      code.symbol: "_check_edit_window"
      code.lines: [93, 102, 231, 232]
      code.error_type: "ValidationError"

tests:
  primary: "tests/training/invariants/test_inv_train_002_wellness_pre_deadline.py"
  node: "TestInvTrain002WellnessPreDeadline"
```

* **Status**: CONFIRMADA
* **Enunciado**: wellness_pre é bloqueado se `NOW > session_at - 2h`
* **Escopo**: `wellness_pre`
* **Onde é imposto**: service (coluna DB documenta regra)
* **Evidência**:
  * `schema.sql:2889` (coluna `locked_at` em `wellness_pre`)
  * `schema.sql:2912` (COMMENT: "pré editável até 2h antes da sessão")
  * `Hb Track - Backend/app/services/wellness_pre_service.py:93-102` (`_check_edit_window`)
  * `Hb Track - Backend/app/services/wellness_pre_service.py:231-232` (ValidationError quando fora da janela)
* **Teste**: `tests/unit/test_inv_train_002_wellness_pre_deadline.py::TestInvTrain002WellnessPreDeadline`

### INV-TRAIN-003 — Deadline Wellness Pós (até 24h após criação)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-003"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "db-column"
    class: "B"
    required: true
    description: "Database column locked_at documents the rule"
    anchors:
      db.table: "wellness_post"
      db.column: "locked_at"
      db.comment: "post editável até 24h após submission"
  
  - unit_key: "service-validation"
    class: "C2"
    required: false
    description: "Service enforces 24h deadline with ValidationError (not yet implemented for edit)"
    anchors:
      code.file: "app/services/wellness_post_service.py"
      code.symbol: "_check_edit_window"
      code.lines: [96, 102, 262, 263]
      code.error_type: "ValidationError"

tests:
  primary: "tests/training/invariants/test_inv_train_003_wellness_post_deadline.py"
  node: "TestInvTrain003WellnessPostDeadline"
```

* **Status**: CONFIRMADA
* **Enunciado**: wellness_post é bloqueado se `NOW > created_at + 24h`
* **Escopo**: `wellness_post`
* **Onde é imposto**: service (coluna DB documenta regra)
* **Evidência**:
  * `schema.sql:2828` (coluna `locked_at` em `wellness_post`)
  * `schema.sql:2863` (COMMENT: "post editável até 24h após submission")
  * `Hb Track - Backend/app/services/wellness_post_service.py:96-102` (`_check_edit_window`)
  * `Hb Track - Backend/app/services/wellness_post_service.py:262-263` (ValidationError quando fora da janela)
* **Teste**: `tests/unit/test_inv_train_003_wellness_post_deadline.py::TestInvTrain003WellnessPostDeadline`

### INV-TRAIN-004 — Janela de edição por autoria/hierarquia e estado

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-004"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Janela de edição por autoria/hierarquia e estado"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.function: "_validate_edit_permission"
      code.constants:
        - "AUTHOR_EDIT_WINDOW_MINUTES"
        - "SUPERIOR_EDIT_WINDOW_HOURS"

tests:
  primary: "tests/unit/test_inv_train_004_edit_window_time.py"
  node: "TestInvTrain004"
```

* **Status**: CONFIRMADA
* **Enunciado**:

  * Autor (treinador): pode editar sessão `scheduled` até **10min** antes de `session_at`
  * Superior (coordenador/dirigente): pode editar `pending_review` até **24h** após `ended_at`
* **Escopo**: `training_sessions` (estados `scheduled` para autor; `pending_review` para superior)
* **Onde é imposto**: service (validações em `_validate_edit_permission`)
* **Evidência**:
  * `Hb Track - Backend/app/services/training_session_service.py:54` (AUTHOR_EDIT_WINDOW_MINUTES = 10)
  * `Hb Track - Backend/app/services/training_session_service.py:55` (SUPERIOR_EDIT_WINDOW_HOURS = 24)
  * `Hb Track - Backend/app/services/training_session_service.py:437-456` (validação por tempo em `_validate_edit_permission`)
* **Teste**: `tests/unit/test_inv_train_004_edit_window_time.py::TestInvTrain004EditWindowTime`

### INV-TRAIN-005 — Sessão > 60 dias vira readonly (imutabilidade)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-005"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Sessão > 60 dias vira readonly (imutabilidade)"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.function: "_validate_edit_permission"
      code.constants:
        - "IMMUTABILITY_DAYS"

tests:
  primary: "tests/unit/test_inv_train_005_immutability_60_days.py"
  node: "TestInvTrain005"
```

* **Status**: CONFIRMADA
* **Escopo**: `training_sessions`
* **Onde é imposto**: service
* **Evidência**:
  * `Hb Track - Backend/app/services/training_session_service.py:58` (IMMUTABILITY_DAYS = 60)
  * `Hb Track - Backend/app/services/training_session_service.py:425-430` (validação em `_validate_edit_permission`)
* **Teste**: `tests/unit/test_inv_train_005_immutability_60_days.py::TestInvTrain005Immutability60Days`

### INV-TRAIN-006 — Lifecycle de status (DB enum + transições operacionais)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-006"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "D"
    required: true
    description: "Lifecycle de status (DB enum + transições operacionais)"
    anchors:
      db.table: "training_sessions"
      db.constraint: "check_training_session_status"
      celery.task: "update_training_session_statuses_task"
      api.operation_id:
        - "publish_training_session_api_v1_training_sessions__training_session_id__publish_post"
        - "close_training_session_api_v1_training_sessions__training_session_id__close_post"

tests:
  primary: "tests/unit/test_inv_train_006_lifecycle_status.py"
  node: "TestInvTrain006"
```

* **Status**: CONFIRMADA
* **Enunciado (DB)**: `draft → scheduled → in_progress → pending_review → readonly`
* **Nota**: UI pode exibir “closed”; no DB o valor é `readonly`
* **Onde é imposto**:

  * DB: enum/constraint de status
  * Service: publish/close
  * Celery: avanço automático `scheduled→in_progress`, `in_progress→pending_review`
* **Evidência**:

  * DB: `check_training_session_status` em `training_sessions` (`schema.sql:2627`)
  * API: `publish_training_session_api_v1_training_sessions__training_session_id__publish_post`
  * API: `close_training_session_api_v1_training_sessions__training_session_id__close_post`
  * Celery: `update_training_session_statuses_task` (`Hb Track - Backend/app/core/celery_tasks.py:581-676`, refs: `617`, `645`)
* **Teste**: `tests/unit/test_inv_train_006_lifecycle_status.py::TestInvTrain006LifecycleStatus`

### INV-TRAIN-007 — Timezone operacional (Celery usa UTC)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-007"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "E1"
    required: true
    description: "Timezone operacional (Celery usa UTC)"
    anchors:
      code.file: "app/core/celery_tasks.py"
      code.function: "update_training_session_statuses_task"
      code.pattern: "datetime.now(timezone.utc)"

tests:
  primary: "tests/training/invariants/test_inv_train_007_celery_utc_timezone.py"
  node: "TestInvTrain007CeleryUtcTimezone"
```

* **Status**: CONFIRMADA
* **Enunciado**: Todas as operações de datetime nas Celery tasks de lifecycle usam UTC (timezone.utc)
* **Escopo**: jobs de lifecycle / automações
* **Onde é imposto**: code (celery tasks)
* **Evidência**:
  * `Hb Track - Backend/app/core/celery_tasks.py:611` (update_training_session_statuses_task: `now = datetime.now(timezone.utc)`)
  * `Hb Track - Backend/app/core/celery_tasks.py:791` (refresh_training_rankings_task)
  * `Hb Track - Backend/app/core/celery_tasks.py:836` (cache.calculated_at)
  * `Hb Track - Backend/app/core/celery_tasks.py:870` (executed_at log)
* **Teste**: `tests/unit/test_inv_train_007_celery_utc_timezone.py::TestInvTrain007CeleryUtcTimezone`

### INV-TRAIN-008 — Soft delete "reason pair" (deleted_at e deleted_reason coerentes)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-008"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "db-constraint-multi-table"
    class: "A"
    required: true
    description: "CHECK constraint pattern across multiple tables (deleted_at/deleted_reason pair)"
    anchors:
      db.pattern: "deleted_at and deleted_reason must both be NULL or both be NOT NULL"
      db.sqlstate: "23514"
      db.constraints:
        - name: "ck_training_sessions_deleted_reason"
          table: "training_sessions"
          schema_line: 2634
        - name: "ck_wellness_pre_deleted_reason"
          table: "wellness_pre"
          schema_line: 2890
        - name: "ck_wellness_post_deleted_reason"
          table: "wellness_post"
          schema_line: 2829
        - name: "ck_attendance_deleted_reason"
          table: "attendance"
          schema_line: 674

tests:
  primary: "tests/training/invariants/test_inv_train_008_soft_delete_reason_pair.py"
  node: "TestInvTrain008SoftDeleteReasonPair"
  note: "Single test file covers all tables (uniform pattern enforcement)"
```

* **Status**: CONFIRMADA
* **Enunciado**: `deleted_at` e `deleted_reason` são ambos NULL ou ambos preenchidos
* **Escopo**: tabelas com constraint confirmada (training_sessions, wellness_pre, wellness_post, attendance)
* **Onde é imposto**: DB constraints
* **Evidência**:
  * `ck_training_sessions_deleted_reason` (`schema.sql:2634`)
  * `ck_wellness_pre_deleted_reason` (`schema.sql:2890`)
  * `ck_wellness_post_deleted_reason` (`schema.sql:2829`)
  * `ck_attendance_deleted_reason` (`schema.sql:674`)
* **Teste**: `tests/unit/test_inv_train_008_soft_delete_reason_pair.py::TestInvTrain008SoftDeleteReasonPair`

### INV-TRAIN-009 — Unicidade: 1 wellness_pre por athlete×session

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-009"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Unicidade: 1 wellness_pre por athlete×session"
    anchors:
      db.table: "wellness_pre"
      db.constraint: "ux_wellness_pre_session_athlete"
      db.sqlstate: "23505"

tests:
  primary: "tests/training/invariants/test_inv_train_009_wellness_pre_uniqueness.py"
  node: "TestInvTrain009WellnessPreUniqueness"
```

* **Status**: CONFIRMADA
* **Enunciado**: Cada atleta só pode ter 1 registro wellness_pre por sessão de treino
* **Escopo**: `wellness_pre`
* **Onde é imposto**: DB unique index (partial)
* **Evidência**: `ux_wellness_pre_session_athlete` (`schema.sql:5187`) - UNIQUE INDEX ON (training_session_id, athlete_id) WHERE deleted_at IS NULL
* **Teste**: `tests/training/invariants/test_inv_train_009_wellness_pre_uniqueness.py::TestInvTrain009WellnessPreUniqueness`

### INV-TRAIN-010 — Unicidade: 1 wellness_post por athlete×session

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-010"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Unicidade: 1 wellness_post por athlete×session"
    anchors:
      db.table: "wellness_post"
      db.constraint: "ux_wellness_post_session_athlete"
      db.sqlstate: "23505"

tests:
  primary: "tests/unit/test_inv_train_010_wellness_post_uniqueness.py"
  node: "TestInvTrain010"
```

* **Status**: CONFIRMADA
* **Enunciado**: Cada atleta só pode ter 1 registro wellness_post por sessão de treino
* **Escopo**: `wellness_post`
* **Onde é imposto**: DB unique index (partial)
* **Evidência**: `ux_wellness_post_session_athlete` (`schema.sql:5180`) - UNIQUE INDEX ON (training_session_id, athlete_id) WHERE deleted_at IS NULL
* **Teste**: `tests/unit/test_inv_train_010_wellness_post_uniqueness.py::TestInvTrain010WellnessPostUniqueness`

### INV-TRAIN-011 — Regras de desvio e justificativa mínima

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-011"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Regras de desvio e justificativa mínima"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.constants:
        - "MIN_JUSTIFICATION_LENGTH"
      code.lines:
        - 916
        - 928

tests:
  primary: "tests/unit/test_inv_train_011_deviation_rules.py"
  node: "TestInvTrain011"
```

* **Status**: CONFIRMADA
* **Enunciado**:
  * desvio significativo: ≥20 pts em qualquer foco
  * desvio agregado significativo: ≥30%
  * justificativa mínima: ≥50 chars
* **Escopo**: `training_sessions` (deviation flow)
* **Onde é imposto**: service
* **Evidência**:
  * `Hb Track - Backend/app/services/training_session_service.py:582` (MIN_JUSTIFICATION_LENGTH = 50)
  * `Hb Track - Backend/app/services/training_session_service.py:916` (desvio individual ≥ 20pts)
  * `Hb Track - Backend/app/services/training_session_service.py:928` (desvio agregado ≥ 30%)
* **Teste**: `tests/unit/test_inv_train_011_deviation_rules.py::TestInvTrain011DeviationRules`

### INV-TRAIN-012 — Rate limiting de export LGPD

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-012"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Rate limiting de export LGPD"
    anchors:
      code.file: "app/services/export_service.py"
      code.constants:
        - "ANALYTICS_PDF_DAILY_LIMIT"
        - "ATHLETE_DATA_DAILY_LIMIT"

tests:
  primary: "tests/unit/test_inv_train_012_export_rate_limit.py"
  node: "TestInvTrain012"
```

* **Status**: CONFIRMADA
* **Enunciado**:
  * PDF: máx 5/dia
  * Athlete export: máx 3/dia
* **Escopo**: exports (compliance)
* **Onde é imposto**: service
* **Evidência**:
  * `Hb Track - Backend/app/services/export_service.py:30` (ANALYTICS_PDF_DAILY_LIMIT = 5)
  * `Hb Track - Backend/app/services/export_service.py:31` (ATHLETE_DATA_DAILY_LIMIT = 3)
* **Teste**: `tests/unit/test_inv_train_012_export_rate_limit.py::TestInvTrain012ExportRateLimit`

### INV-TRAIN-013 — Gamificação: critérios de badge (regras de elegibilidade)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-013"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Gamificação: critérios de badge (regras de elegibilidade)"
    anchors:
      code.file: "app/services/wellness_gamification_service.py"
      code.function: "_check_and_award_streak"
      code.lines:
        - 128
        - 147
        - 389

tests:
  primary: "tests/unit/test_inv_train_013_gamification_badge_rules.py"
  node: "TestInvTrain013"
```

* **Status**: CONFIRMADA
* **Enunciado**:
  * monthly: response_rate ≥ 90%
  * streak: 3 meses consecutivos
* **Escopo**: gamification
* **Onde é imposto**: service
* **Evidência**:
  * `Hb Track - Backend/app/services/wellness_gamification_service.py:128` (response_rate >= 90.0)
  * `Hb Track - Backend/app/services/wellness_gamification_service.py:147-154` (_check_and_award_streak)
  * `Hb Track - Backend/app/services/wellness_gamification_service.py:389-450` (streak de 3 meses)
* **Teste**: `tests/unit/test_inv_train_013_gamification_badge_rules.py::TestInvTrain013GamificationBadgeRules`

### INV-TRAIN-014 — Alertas: sobrecarga por multiplicador (>= 1.5× threshold)
**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-014"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Alertas: sobrecarga por multiplicador (>= 1.5× threshold)"
    anchors:
      code.file: "app/services/training_alerts_service.py"
      code.constants:
        - "alert_threshold_multiplier"

tests:
  primary: "tests/unit/test_inv_train_014_overload_alert_threshold.py"
  node: "TestInvTrain014"
```
* **Status**: CONFIRMADA
* **Enunciado**: Alertas de sobrecarga são disparados quando carga >= 1.5× do threshold base
* **Escopo**: alerts/suggestions
* **Onde é imposto**: service
* **Evidência**:
  * `Hb Track - Backend/app/services/training_alerts_service.py:43` (alert_threshold_multiplier: float = 1.5)
  * `Hb Track - Backend/app/services/training_alerts_service.py:51` (documentação: default 1.5 = 150%)
  * `Hb Track - Backend/app/services/training_alerts_service.py:82` (threshold_critical = threshold_base * alert_threshold_multiplier)
* **Teste**: `tests/unit/test_inv_train_014_overload_alert_threshold.py::TestInvTrain014OverloadAlertThreshold`

### INV-TRAIN-015 — Training Analytics (FR-012) exposto e ancorado em router/service

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-015"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C1"
    required: true
    description: "Training Analytics (FR-012) exposto e ancorado em router/service"
    anchors:
      code.router_file: "app/api/v1/routers/training_analytics.py"
      code.router_symbols:
        - "get_team_summary"
        - "get_weekly_load"
        - "get_deviation_analysis"
        - "get_prevention_effectiveness"
      code.service_file: "app/services/training_analytics_service.py"
      code.service_symbol: "TrainingAnalyticsService"

tests:
  primary: "tests/training/invariants/test_inv_train_015_training_analytics_exposure.py"
  node: "TestInvTrain015TrainingAnalyticsExposure"
```

* **Status**: CONFIRMADA
* **Enunciado**: Módulo Training Analytics expõe 4 endpoints via router e ancora em services, incluindo threshold dinâmico via team.alert_threshold_multiplier
* **Escopo**: analytics team endpoints
* **Onde é imposto**: router + services
* **Evidência**:
  * Router: `Hb Track - Backend/app/api/v1/routers/training_analytics.py:30-204` (4 endpoints: summary, weekly-load, deviation-analysis, prevention-effectiveness)
  * Services: `Hb Track - Backend/app/services/training_analytics_service.py:29-38` (TrainingAnalyticsService)
  * Services: `Hb Track - Backend/app/services/prevention_effectiveness_service.py:17-20` (PreventionEffectivenessService)
  * Threshold dinâmico: `Hb Track - Backend/app/services/training_analytics_service.py:191` (team.alert_threshold_multiplier)
* **Teste**: `tests/unit/test_inv_train_015_training_analytics_exposure.py::TestInvTrain015TrainingAnalyticsExposure`

### INV-TRAIN-016 — Attendance: rota base exige auth; rota scoped não exposta

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-016"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "D"
    required: true
    description: "Attendance: rota base exige auth; rota scoped não exposta"
    anchors:
      api.operation_id: "list_attendance_by_session_api_v1_training_sessions__training_session_id__attendance_get"
      code.file: "app/api/v1/routers/attendance.py"
      code.auth: "required"
      code.note: "attendance_scoped não exposto em api.py"

tests:
  primary: "tests/training/invariants/test_inv_train_016_attendance_auth_scoped.py"
  node: "TestInvTrain016AttendanceAuthScoped"
```

* **Status**: CONFIRMADA
* **Escopo**: Attendance API
* **Onde é imposto**: router (auth) + agregador de rotas (contrato)
* **Evidência**:

  * Auth obrigatório na rota base: `Hb Track - Backend/app/api/v1/routers/attendance.py:54-59`
  * Rotas scoped definidas, mas não expostas: `Hb Track - Backend/app/api/v1/routers/attendance_scoped.py:162-203`
  * Agregador inclui `attendance.router` (sem `attendance_scoped`): `Hb Track - Backend/app/api/v1/api.py:184-186`
* **Teste**:

  * `tests/api/test_training.py::TestAttendanceAPI::test_attendance_route_without_auth_returns_401`
  * `tests/api/test_training.py::TestAttendanceAPI::test_scoped_attendance_route_not_exposed_returns_404`

### INV-TRAIN-028 — Focus ≤120% em training_sessions

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-028"
status: "CONFIRMADA"
test_required: false
canonical_id: "INV-TRAIN-001"
legacy_reason: "Same constraint ck_training_sessions_focus_total_sum. INV-TRAIN-001 is canonical."
alias_type: "subset"

units:
  - unit_key: "reference-to-canonical"
    class: "A"
    required: false
    description: "References same constraint as INV-TRAIN-001 unit 'db-constraint-training-sessions'"
    anchors:
      db.table: "training_sessions"
      db.constraint: "ck_training_sessions_focus_total_sum"
      db.sqlstate: "23514"

tests:
  primary: "tests/training/invariants/test_inv_train_001_focus_sum_constraint.py"
  note: "Covered by canonical INV-TRAIN-001 test"
```

* Legacy ID: INV-TRAIN-P011
* **Status**: CONFIRMADA
* **Escopo**: `training_sessions`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2640` (`ck_training_sessions_focus_total_sum`)
* **Teste**: `tests/unit/test_inv_train_028_focus_sum_constraint.py::TestInvTrain028FocusSumConstraint`

### INV-TRAIN-020 — Cache invalidation automático após mudanças em sessões

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-020"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Cache invalidation automático após mudanças em sessões"
    anchors:
      db.table: "training_sessions"
      db.trigger: "tr_invalidate_analytics_cache"

tests:
  primary: "tests/unit/test_inv_train_020_cache_invalidation_trigger.py"
  node: "TestInvTrain020"
```

* Legacy ID: INV-TRAIN-P003
* **Status**: CONFIRMADA
* **Escopo**: `training_sessions` → `training_analytics_cache`
* **Onde é imposto**: DB trigger
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:5208` (`tr_invalidate_analytics_cache`)
* **Teste**: `tests/unit/test_inv_train_020_cache_invalidation_trigger.py::TestInvTrain020CacheInvalidationTrigger`

### INV-TRAIN-021 — Internal load calculado por trigger no DB

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-021"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Internal load calculado por trigger no DB"
    anchors:
      db.table: "wellness_post"
      db.trigger: "tr_calculate_internal_load"

tests:
  primary: "tests/unit/test_inv_train_021_internal_load_trigger.py"
  node: "TestInvTrain021"
```

* Legacy ID: INV-TRAIN-P004
* **Status**: CONFIRMADA
* **Escopo**: `wellness_post`
* **Onde é imposto**: DB trigger
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:5194` (`tr_calculate_internal_load`)
* **Teste**: `tests/unit/test_inv_train_021_internal_load_trigger.py::TestInvTrain021InternalLoadTrigger`

### INV-TRAIN-040 — Contrato OpenAPI para endpoint health (Classe F)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-040"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "F"
    required: true
    description: "Contrato OpenAPI para endpoint health - validação contra openapi.json"
    anchors:
      api.operation_id: "health_api_v1_health_get"
      api.method: "GET"
      api.path: "/api/v1/health"
      api.responses:
        - "200"
      api.security: "none"

tests:
  primary: "tests/training/invariants/test_inv_train_040_health_contract.py"
  node: "TestInvTrain040HealthContract"
```

* **Status**: CONFIRMADA
* **Escopo**: Health endpoint OpenAPI contract
* **Onde é imposto**: OpenAPI specification (docs/_generated/openapi.json)
* **Evidência**: FastAPI auto-generated OpenAPI schema
* **Teste**: `tests/training/invariants/test_inv_train_040_health_contract.py::TestInvTrain040HealthContract`

---

### INV-TRAIN-041 — Contrato OpenAPI para endpoint teams com autenticação (Classe F) owner: teams

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-041"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "F"
    required: true
    description: "Contrato OpenAPI para endpoint teams - validação com security"
    anchors:
      api.operation_id: "get_teams_api_v1_teams_get"
      api.method: "GET"
      api.path: "/api/v1/teams"
      api.responses:
        - "200"
        - "422"
      api.security:
        - "HTTPBearer"

tests:
  primary: "tests/training/invariants/test_inv_train_041_teams_contract.py"
  node: "TestInvTrain041TeamsContract"
```

* **Status**: CONFIRMADA
* **Escopo**: Teams endpoint OpenAPI contract with authentication
* **Onde é imposto**: OpenAPI specification (docs/_generated/openapi.json)
* **Evidência**: FastAPI auto-generated OpenAPI schema with HTTPBearer security
* **Teste**: `tests/training/invariants/test_inv_train_041_teams_contract.py::TestInvTrain041TeamsContract`

---

### INV-TRAIN-022 — Atualização automática de performance cache ao registrar wellness_post

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-022"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Atualização automática de performance cache ao registrar wellness_post"
    anchors:
      code.file: "app/services/wellness_post_service.py"
      code.lines:
        - 268
        - 324

tests:
  primary: "tests/unit/test_wellness_post_cache_invalidation.py"
  node: "TestInvTrain022"
```

* Legacy ID: INV-TRAIN-P005
* **Status**: CONFIRMADA
* **Escopo**: `wellness_post` → `training_analytics_cache`
* **Onde é imposto**: service
* **Evidência**: `Hb Track - Backend/app/services/wellness_post_service.py:268-324`
* **Teste**: `tests/unit/test_wellness_post_cache_invalidation.py::test_invalidate_training_analytics_cache_marks_weekly_and_monthly`

### INV-TRAIN-024 — WebSocket broadcast e NotificationService para alerts/badges

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-024"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "WebSocket broadcast e NotificationService para alerts/badges"
    anchors:
      code.file:
        - "app/services/training_alerts_service.py"
        - "app/services/wellness_gamification_service.py"
      code.lines:
        - 364
        - 328

tests:
  primary: "tests/unit/test_inv_train_024_websocket_broadcast.py"
  node: "TestInvTrain024"
```

* Legacy ID: INV-TRAIN-P007
* **Status**: CONFIRMADA
* **Escopo**: notifications (alerts/badges)
* **Onde é imposto**: services
* **Evidência**:

  * `Hb Track - Backend/app/services/training_alerts_service.py:364-413` (alertas críticos → NotificationService + broadcast)
  * `Hb Track - Backend/app/services/wellness_gamification_service.py:328-387` (badges → NotificationService + broadcast)
* **Teste**: `tests/unit/test_inv_train_024_websocket_broadcast.py::TestInvTrain024WebsocketBroadcast`

### INV-TRAIN-025 — Export LGPD via endpoints OpenAPI + Celery async + cleanup de jobs

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-025"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C1"
    required: true
    description: "Export LGPD via endpoints OpenAPI + Celery async + cleanup de jobs"
    anchors:
      code.file:
        - "app/api/v1/routers/exports.py"
        - "app/api/v1/routers/athlete_export.py"
      celery.task:
        - "generate_analytics_pdf_task"
        - "cleanup_expired_export_jobs_task"

tests:
  primary: "tests/unit/test_inv_train_025_export_lgpd_endpoints.py"
  node: "TestInvTrain025"
```

* Legacy ID: INV-TRAIN-P008
* **Status**: CONFIRMADA
* **Escopo**: `export_jobs` / LGPD export
* **Onde é imposto**: router + celery tasks
* **Evidência**:

  * `Hb Track - Backend/app/api/v1/routers/exports.py:32-170` (export PDF analytics + status/list/rate-limit)
  * `Hb Track - Backend/app/api/v1/routers/athlete_export.py:29-120` (LGPD export /athletes/me/export-data)
  * `Hb Track - Backend/app/core/celery_tasks.py:400-556` (generate_analytics_pdf_task + cleanup_expired_export_jobs_task)
* **Teste**: `tests/unit/test_inv_train_025_export_lgpd_endpoints.py::TestInvTrain025ExportLgpdEndpoints`

### INV-TRAIN-026 — LGPD access logging (staff lendo dados de outros atletas)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-026"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "LGPD access logging (staff lendo dados de outros atletas)"
    anchors:
      code.file:
        - "app/services/wellness_pre_service.py"
        - "app/services/wellness_post_service.py"
      code.pattern: "data_access_logs"

tests:
  primary: "tests/unit/test_inv_train_026_lgpd_access_logging.py"
  node: "TestInvTrain026"
```

* Legacy ID: INV-TRAIN-P009
* **Status**: CONFIRMADA
* **Escopo**: `wellness_pre` / `wellness_post`
* **Onde é imposto**: services
* **Evidência**:

  * `Hb Track - Backend/app/services/wellness_pre_service.py:69-173` (data_access_logs para staff)
  * `Hb Track - Backend/app/services/wellness_post_service.py:69-169` (data_access_logs para staff)
* **Teste**: `tests/unit/test_inv_train_026_lgpd_access_logging.py::TestInvTrain026LgpdAccessLogging`

### INV-TRAIN-018 — Sessões criadas via microciclo: draft se incompleta, scheduled se completa

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-018"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Sessões criadas via microciclo: draft se incompleta, scheduled se completa"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.function: "create"
      code.lines:
        - 237
        - 239

tests:
  primary: "Hb Track - Backend/tests/unit/test_training_session_microcycle_status.py"
  node: "TestInvTrain018"
```

* Legacy ID: INV-TRAIN-P001
* **Status**: CONFIRMADA
* **Escopo**: microcycle → sessions generation/default status
* **Onde é imposto**: service (training_session_service.create)
* **Evidência**: `Hb Track - Backend/app/services/training_session_service.py:237-239`
* **Teste**: `Hb Track - Backend/tests/unit/test_training_session_microcycle_status.py::test_microcycle_session_status_respects_completeness`; `Hb Track - Backend/tests/integration/test_training_session_microcycle_status_route.py::test_create_training_session_with_microcycle_sets_expected_status`

### INV-TRAIN-019 — Audit log para ações de sessão (create/edit/publish/close)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-019"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Audit log para ações de sessão (create/edit/publish/close)"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.functions:
        - "create"
        - "update"
        - "publish"
        - "close"
      code.lines:
        - 246
        - 341
        - 393
        - 764
        - 786

tests:
  primary: "Hb Track - Backend/tests/integration/test_training_session_audit_logs.py"
  node: "TestInvTrain019"
```

* Legacy ID: INV-TRAIN-P002
* **Status**: CONFIRMADA
* **Escopo**: `training_sessions` (audit_logs)
* **Onde é imposto**: service (training_session_service)
* **Evidência**: `Hb Track - Backend/app/services/training_session_service.py:246-255` (create), `Hb Track - Backend/app/services/training_session_service.py:341-348` (update), `Hb Track - Backend/app/services/training_session_service.py:393-399` (publish), `Hb Track - Backend/app/services/training_session_service.py:764-770` (close), `Hb Track - Backend/app/services/training_session_service.py:786-828` (insert em audit_logs)
* **Teste**: `Hb Track - Backend/tests/integration/test_training_session_audit_logs.py::test_audit_logs_for_create_update_publish_and_close`

### INV-TRAIN-027 — Cache refresh daily para rankings/métricas

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-027"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "D"
    required: true
    description: "Cache refresh daily para rankings/métricas"
    anchors:
      celery.schedule: "refresh-analytics-cache"
      celery.task: "refresh_training_rankings_task"
      code.file:
        - "app/core/celery_app.py"
        - "app/core/celery_tasks.py"

tests:
  primary: "tests/unit/test_refresh_training_rankings_task.py"
  node: "TestInvTrain027"
```

* Legacy ID: INV-TRAIN-P010
* **Status**: CONFIRMADA
* **Escopo**: training_analytics_cache / rankings
* **Onde é imposto**: Celery beat schedule + task
* **Evidência**:
  * Schedule: `Hb Track - Backend/app/core/celery_app.py:117` (`refresh-analytics-cache`)
  * Task: `Hb Track - Backend/app/core/celery_tasks.py:768` (`refresh_training_rankings_task`)
* **Teste**: `tests/unit/test_refresh_training_rankings_task.py::test_refresh_training_rankings_task_recalculates_dirty_caches`

### INV-TRAIN-023 — Overload alerts disparados automaticamente por wellness_post

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-023"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Overload alerts disparados automaticamente por wellness_post"
    anchors:
      code.file: "app/services/wellness_post_service.py"
      code.function: "_trigger_overload_alert_on_wellness_post"

tests:
  primary: "Hb Track - Backend/tests/unit/test_wellness_post_overload_alert_trigger.py"
  node: "TestInvTrain023"
```

* Legacy ID: INV-TRAIN-P006
* **Status**: CONFIRMADA
* **Escopo**: wellness_post → training_alerts
* **Onde é imposto**: service hook no submit do wellness_post
* **Evidência**: `Hb Track - Backend/app/services/wellness_post_service.py:330` (helper `_trigger_overload_alert_on_wellness_post`)
* **Teste**: `Hb Track - Backend/tests/unit/test_wellness_post_overload_alert_trigger.py::test_trigger_overload_alert_on_wellness_post_uses_session_week_and_team_multiplier`

### INV-TRAIN-029 — Edição bloqueada após início da sessão

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-029"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Edição bloqueada após início da sessão"
    anchors:
      code.file: "app/services/training_session_service.py"
      code.function: "_validate_edit_permission"
      code.lines:
        - 441
        - 444
        - 447
        - 460

tests:
  primary: "tests/unit/test_inv_train_029_edit_blocked_after_in_progress.py"
  node: "TestInvTrain029"
```

* **Status**: CONFIRMADA
* **Enunciado**: Edição de `training_sessions` é bloqueada por estado:
  * `readonly` → bloqueia completamente ("Sessão congelada. Revisão já concluída.")
  * `in_progress` → bloqueia completamente ("Sessão em andamento não pode ser editada.")
  * `pending_review` → permite apenas campos de revisão (execution_outcome, delay_minutes, etc.)
  * `scheduled` → permite apenas campos específicos (notes, focus_*, intensity_target, etc.)
  * `draft` → permite edição livre
* **Escopo**: `training_sessions`
* **Onde é imposto**: service (`_validate_edit_permission`)
* **Evidência**:
  * `Hb Track - Backend/app/services/training_session_service.py:441-442` (readonly → ForbiddenError)
  * `Hb Track - Backend/app/services/training_session_service.py:444-445` (in_progress → ForbiddenError)
  * `Hb Track - Backend/app/services/training_session_service.py:447-458` (pending_review → campos de revisão)
  * `Hb Track - Backend/app/services/training_session_service.py:460-480` (scheduled → campos específicos)
* **Teste**: `tests/unit/test_inv_train_029_edit_blocked_after_in_progress.py::TestInvTrain029EditBlockedAfterInProgress`

### INV-TRAIN-030 — Correção de attendance exige campos de auditoria

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-030"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Correção de attendance exige campos de auditoria"
    anchors:
      db.table: "attendance"
      db.constraint: "ck_attendance_correction_fields"
      db.sqlstate: "23514"

tests:
  primary: "tests/unit/test_inv_train_030_attendance_correction_fields.py"
  node: "TestInvTrain030"
```

* **Status**: CONFIRMADA
* **Enunciado**: Quando `source = 'correction'`, os campos `correction_by_user_id` e `correction_at` devem estar preenchidos
* **Escopo**: `attendance`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:673` (`ck_attendance_correction_fields`)
* **Comentário DB**: "Garante que correções têm correction_by_user_id e correction_at preenchidos" (`schema.sql:707`)
* **Teste**: `tests/unit/test_inv_train_030_attendance_correction_fields.py`

### INV-TRAIN-031 — Derivação automática de phase_focus a partir dos percentuais

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-031"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Derivação automática de phase_focus a partir dos percentuais"
    anchors:
      db.table: "training_sessions"
      db.trigger: "tr_derive_phase_focus"
      db.function: "fn_derive_phase_focus"
      db.constraints:
        - "ck_phase_focus_attack_consistency"
        - "ck_phase_focus_defense_consistency"
        - "ck_phase_focus_transition_defense_consistency"
        - "ck_phase_focus_transition_offense_consistency"

tests:
  primary: "tests/unit/test_inv_train_031_derive_phase_focus.py"
  node: "TestInvTrain031"
```

* **Status**: CONFIRMADA
* **Enunciado**: Os campos booleanos `phase_focus_attack`, `phase_focus_defense`, `phase_focus_transition_offense` e `phase_focus_transition_defense` são derivados automaticamente quando a soma dos percentuais correspondentes ≥ 5%
* **Escopo**: `training_sessions`
* **Onde é imposto**: DB trigger + constraints
* **Evidência**:
  * Trigger: `Hb Track - Backend/docs/_generated/schema.sql:5201` (`tr_derive_phase_focus`)
  * Função: `Hb Track - Backend/docs/_generated/schema.sql:190-220` (`fn_derive_phase_focus`)
  * Constraints de consistência:
    * `schema.sql:2629` (`ck_phase_focus_attack_consistency`)
    * `schema.sql:2630` (`ck_phase_focus_defense_consistency`)
    * `schema.sql:2631` (`ck_phase_focus_transition_defense_consistency`)
    * `schema.sql:2632` (`ck_phase_focus_transition_offense_consistency`)
* **Comentário DB**: "Step 3: Deriva automaticamente phase_focus_* baseado no threshold de 5%" (`schema.sql:227`)
* **Teste**: `tests/unit/test_inv_train_031_derive_phase_focus.py`

### INV-TRAIN-032 — RPE da sessão deve estar entre 0 e 10

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-032"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "RPE da sessão deve estar entre 0 e 10"
    anchors:
      db.table: "wellness_post"
      db.constraint: "ck_wellness_post_rpe"
      db.sqlstate: "23514"

tests:
  primary: "tests/training/invariants/test_inv_train_032_*.py"
  node: "TestInvTrain032"
```

* **Status**: CONFIRMADA
* **Enunciado**: O campo `session_rpe` em wellness_post deve estar no intervalo [0, 10]
* **Escopo**: `wellness_post`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2833` (`ck_wellness_post_rpe`)
* **Teste**:
  * Contract: `tests/unit/test_inv_train_032_wellness_post_rpe.py`
  * Runtime: `tests/integration/test_inv_train_032_wellness_post_rpe_runtime.py`

### INV-TRAIN-033 — Horas de sono deve estar entre 0 e 24

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-033"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Horas de sono deve estar entre 0 e 24"
    anchors:
      db.table: "wellness_pre"
      db.constraint: "ck_wellness_pre_sleep_hours"
      db.sqlstate: "23514"

tests:
  primary: "tests/training/invariants/test_inv_train_033_wellness_pre_sleep_hours.py"
  node: "TestInvTrain033WellnessPreSleepHours"
```

* **Status**: CONFIRMADA
* **Enunciado**: O campo `sleep_hours` em wellness_pre deve estar no intervalo [0, 24]
* **Escopo**: `wellness_pre`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2894` (`ck_wellness_pre_sleep_hours`)
* **Teste**: `tests/unit/test_inv_train_033_wellness_pre_sleep_hours.py`

### INV-TRAIN-034 — Qualidade do sono deve estar entre 1 e 5

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-034"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Qualidade do sono deve estar entre 1 e 5"
    anchors:
      db.table: "wellness_pre"
      db.constraint: "ck_wellness_pre_sleep_quality"
      db.sqlstate: "23514"

tests:
  primary: "tests/unit/test_inv_train_034_wellness_pre_sleep_quality.py"
  node: "TestInvTrain034"
```

* **Status**: CONFIRMADA
* **Enunciado**: O campo `sleep_quality` em wellness_pre deve estar no intervalo [1, 5]
* **Escopo**: `wellness_pre`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2895` (`ck_wellness_pre_sleep_quality`)
* **Teste**: `tests/unit/test_inv_train_034_wellness_pre_sleep_quality.py`

### INV-TRAIN-035 — Nome de template de sessão é único por organização

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-035"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Nome de template de sessão é único por organização"
    anchors:
      db.table: "session_templates"
      db.constraint: "uq_session_templates_org_name"
      db.sqlstate: "23505"

tests:
  primary: "tests/unit/test_inv_train_035_session_templates_unique_name.py"
  node: "TestInvTrain035"
```

* **Status**: CONFIRMADA
* **Enunciado**: Não pode haver dois templates de sessão com o mesmo `name` na mesma `org_id`
* **Escopo**: `session_templates`
* **Onde é imposto**: DB constraint (UNIQUE)
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:3645` (`uq_session_templates_org_name`)
* **Teste**: `tests/unit/test_inv_train_035_session_templates_unique_name.py`

### INV-TRAIN-036 — Ranking de wellness é único por time e mês

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-036"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Ranking de wellness é único por time e mês"
    anchors:
      db.table: "team_wellness_rankings"
      db.constraint: "uq_team_wellness_rankings_team_month"
      db.sqlstate: "23505"

tests:
  primary: "tests/unit/test_inv_train_036_wellness_rankings_unique.py"
  node: "TestInvTrain036"
```

* **Status**: CONFIRMADA
* **Enunciado**: Não pode haver dois registros de ranking para o mesmo `team_id` e `month_reference`
* **Escopo**: `team_wellness_rankings`
* **Onde é imposto**: DB constraint (UNIQUE)
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:3653` (`uq_team_wellness_rankings_team_month`)
* **Teste**: `tests/unit/test_inv_train_036_wellness_rankings_unique.py`

### INV-TRAIN-037 — Data de início do ciclo deve ser anterior à data de término

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-037"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Data de início do ciclo deve ser anterior à data de término"
    anchors:
      db.table: "training_cycles"
      db.constraint: "check_cycle_dates"
      db.sqlstate: "23514"

tests:
  primary: "tests/training/invariants/test_inv_train_037_*.py"
  node: "TestInvTrain037"
```

* **Status**: CONFIRMADA
* **Enunciado**: O campo `start_date` deve ser menor que `end_date` em training_cycles
* **Escopo**: `training_cycles`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2402` (`check_cycle_dates`)
* **Teste**:
  * Contract: `tests/unit/test_inv_train_037_cycle_dates.py`
  * Runtime: `tests/integration/test_inv_train_037_cycle_dates_runtime.py`

---

### INV-TRAIN-043 — Data de início do microciclo deve ser anterior à data de término

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-043"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "CHECK constraint garante week_start < week_end em microciclos"
    anchors:
      db.table: "training_microcycles"
      db.constraint: "check_microcycle_dates"
      db.type: "CHECK"
      db.source: "schema.sql:2462"
      db.sqlstate: "23514"

tests:
  primary: "tests/training/invariants/test_inv_train_043_microcycle_dates_check.py"
  node: "TestInvTrain043MicrocycleDatesCheck"
```

* **Status**: CONFIRMADA
* **Enunciado**: O campo `week_start` deve ser menor que `week_end` em training_microcycles
* **Escopo**: `training_microcycles`
* **Onde é imposto**: DB constraint
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:2462` (`check_microcycle_dates`)
* **Teste**: `tests/training/invariants/test_inv_train_043_microcycle_dates_check.py`

---

### INV-TRAIN-044 — Unicidade de cache lookup (team + microcycle + month + granularity)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-044"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "UNIQUE constraint garante unicidade de cache por team/microcycle/month/granularity"
    anchors:
      db.table: "training_analytics_cache"
      db.constraint: "uq_training_analytics_cache_lookup"
      db.type: "UNIQUE"
      db.source: "schema.sql:3661"
      db.sqlstate: "23505"
      db.columns: ["team_id", "microcycle_id", "month", "granularity"]

tests:
  primary: "tests/training/invariants/test_inv_train_044_analytics_cache_unique.py"
  node: "TestInvTrain044AnalyticsCacheUnique"
```

* **Status**: CONFIRMADA
* **Enunciado**: Não pode haver dois registros de cache com a mesma combinação de (team_id, microcycle_id, month, granularity)
* **Escopo**: `training_analytics_cache`
* **Onde é imposto**: DB constraint (UNIQUE)
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:3661` (`uq_training_analytics_cache_lookup`)
* **Teste**: `tests/training/invariants/test_inv_train_044_analytics_cache_unique.py`

---

### INV-TRAIN-045 — Unicidade de order_index por sessão de treino

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-045"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "UNIQUE INDEX garante unicidade de order_index por sessão (partial, WHERE deleted_at IS NULL)"
    anchors:
      db.table: "training_session_exercises"
      db.constraint: "idx_session_exercises_session_order_unique"
      db.type: "UNIQUE INDEX (partial)"
      db.source: "schema.sql:3917"
      db.sqlstate: "23505"
      db.columns: ["session_id", "order_index"]
      db.condition: "WHERE deleted_at IS NULL"

tests:
  primary: "tests/training/invariants/test_inv_train_045_session_exercises_order_unique.py"
  node: "TestInvTrain045SessionExercisesOrderUnique"
```

* **Status**: CONFIRMADA
* **Enunciado**: Não pode haver dois exercícios com o mesmo `order_index` na mesma sessão de treino (quando não deletados)
* **Escopo**: `training_session_exercises`
* **Onde é imposto**: DB UNIQUE INDEX (partial)
* **Evidência**: `Hb Track - Backend/docs/_generated/schema.sql:3917` (`idx_session_exercises_session_order_unique`)
* **Teste**: `tests/training/invariants/test_inv_train_045_session_exercises_order_unique.py`

---

### INV-TRAIN-046 — Trigger atualiza responded_at em wellness_reminders ao inserir wellness_post

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-046"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "B"
    required: true
    description: "Trigger AFTER INSERT em wellness_post atualiza responded_at em wellness_reminders"
    anchors:
      db.table: "wellness_post"
      db.trigger: "tr_update_wellness_post_response"
      db.function: "fn_update_wellness_response_timestamp"
      db.source_trigger: "schema.sql:5222"
      db.source_function: "schema.sql:287"
      db.effect: "UPDATE wellness_reminders SET responded_at = NOW() WHERE training_session_id = NEW.training_session_id AND athlete_id = NEW.athlete_id AND responded_at IS NULL"

tests:
  primary: "tests/training/invariants/test_inv_train_046_wellness_post_response_trigger.py"
  node: "TestInvTrain046WellnessPostResponseTrigger"
```

* **Status**: CONFIRMADA
* **Enunciado**: Ao inserir um `wellness_post`, o trigger `tr_update_wellness_post_response` atualiza automaticamente o campo `responded_at` em `wellness_reminders` para o mesmo atleta e sessão
* **Escopo**: `wellness_post`, `wellness_reminders`
* **Onde é imposto**: DB trigger + function
* **Evidência**:
  * `schema.sql:5222` (trigger `tr_update_wellness_post_response`)
  * `schema.sql:287` (function `fn_update_wellness_response_timestamp`)
* **Teste**: `tests/training/invariants/test_inv_train_046_wellness_post_response_trigger.py`

### INV-TRAIN-047 — Bulk add session exercises limitado a 50 itens

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-047"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Bulk add de exercícios a sessão limitado a 50 itens via schema Pydantic"
    anchors:
      code.file: "Hb Track - Backend/app/schemas/session_exercises.py"
      code.symbol: "SessionExerciseBulkCreate.exercises"
      code.constraint: "Field(..., min_length=1, max_length=50)"

tests:
  primary: "tests/training/invariants/test_inv_train_047_bulk_add_limit.py"
  node: "TestInvTrain047BulkAddLimit"
```

* **Status**: CONFIRMADA
* **Enunciado**: O endpoint de bulk add de exercícios a uma sessão aceita no mínimo 1 e no máximo 50 exercícios por request
* **Escopo**: `training_session_exercises` (via endpoint bulk add)
* **Onde é imposto**: Schema Pydantic (`SessionExerciseBulkCreate.exercises: list[SessionExerciseCreate] = Field(..., min_length=1, max_length=50)`)
* **Evidência**: `Hb Track - Backend/app/schemas/session_exercises.py:48`
* **Teste**: Pendente criação

### INV-TRAIN-048 — Limite de 50 templates por organização

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-048"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Limite de 50 templates por organização, imposto no router"
    anchors:
      code.file: "Hb Track - Backend/app/api/v1/routers/session_templates.py"
      code.function: "create_session_template"
      code.line: "110-122"
      code.constraint: "count >= 50 → HTTPException 422"

tests:
  primary: "tests/training/invariants/test_inv_train_048_template_org_limit.py"
  node: "TestInvTrain048TemplateOrgLimit"
```

* **Status**: CONFIRMADA
* **Enunciado**: Uma organização não pode ter mais de 50 session templates; ao atingir o limite, criação retorna 422
* **Escopo**: `session_templates`
* **Onde é imposto**: Router (`session_templates.py:110-122` — `count >= 50` → HTTPException 422 com mensagem "Limite de 50 templates por organização atingido")
* **Evidência**: `Hb Track - Backend/app/api/v1/routers/session_templates.py:117`
* **Teste**: Pendente criação

### INV-TRAIN-049 — Constantes do algoritmo de sugestões de carga

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-049"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C1"
    required: true
    description: "Algoritmo de sugestões requer mínimo 3 microciclos, desvio ≥10pts, lookback 90 dias"
    anchors:
      code.file: "Hb Track - Backend/app/services/training_suggestion_service.py"
      code.class: "TrainingSuggestionService"
      code.constants:
        MIN_MICROCYCLES_FOR_SUGGESTION: 3
        MIN_DEVIATION_THRESHOLD: 10.0
        LOOKBACK_DAYS: 90

tests:
  primary: "tests/training/invariants/test_inv_train_049_suggestion_constraints.py"
  node: "TestInvTrain049SuggestionConstraints"
```

* **Status**: CONFIRMADA
* **Enunciado**: O algoritmo de sugestões de carga só gera sugestões quando: (a) existem ≥3 microciclos similares no período, (b) o desvio é ≥10 pontos percentuais, (c) o lookback cobre os últimos 90 dias
* **Escopo**: `training_suggestions` (geração via service)
* **Onde é imposto**: Service (`training_suggestion_service.py:39-41` — constants `MIN_MICROCYCLES_FOR_SUGGESTION=3`, `MIN_DEVIATION_THRESHOLD=10.0`, `LOOKBACK_DAYS=90`)
* **Evidência**: `Hb Track - Backend/app/services/training_suggestion_service.py:39-41,70,121,210`
* **Teste**: Pendente criação

### INV-TRAIN-050 — Validação anti-ciclo em tags de exercícios

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-050"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "C2"
    required: true
    description: "Atribuição de parent_tag_id a uma tag não pode criar ciclo na hierarquia"
    anchors:
      code.file: "Hb Track - Backend/app/services/exercise_service.py"
      code.function: "_validate_no_cycle"
      code.line: "29-69"
      code.algorithm: "Depth-first traversal dos ancestrais; se encontrar tag_id → HTTPException 400"

tests:
  primary: "tests/training/invariants/test_inv_train_050_tag_anti_cycle.py"
  node: "TestInvTrain050TagAntiCycle"
```

* **Status**: CONFIRMADA
* **Enunciado**: Ao atualizar `parent_tag_id` de uma exercise_tag, o sistema percorre a árvore de ancestrais e rejeita (HTTP 400) se a operação criaria um ciclo na hierarquia
* **Escopo**: `exercise_tags` (via update tag)
* **Onde é imposto**: Service (`exercise_service.py:29-69` — `_validate_no_cycle()`: self-reference check + DFS traversal + visited set para detectar ciclos pré-existentes)
* **Evidência**: `Hb Track - Backend/app/services/exercise_service.py:29,46,64,190`
* **Teste**: Pendente criação

### INV-TRAIN-051 — Exercícios duplicados permitidos em sessão (circuitos)

**SPEC**:
```yaml
spec_version: "1.0"
id: "INV-TRAIN-051"
status: "CONFIRMADA"
test_required: true

units:
  - unit_key: "main"
    class: "A"
    required: true
    description: "Tabela training_session_exercises não possui UNIQUE em (session_id, exercise_id), permitindo duplicatas para circuitos"
    anchors:
      db.table: "training_session_exercises"
      db.absence: "Sem UNIQUE constraint em (session_id, exercise_id)"
      code.file: "Hb Track - Backend/app/models/session_exercise.py"
      code.comment: "Allows DUPLICATES: same exercise can appear multiple times"

tests:
  primary: "tests/training/invariants/test_inv_train_051_exercise_duplicates.py"
  node: "TestInvTrain051ExerciseDuplicates"
```

* **Status**: CONFIRMADA
* **Enunciado**: Uma sessão de treino pode conter o mesmo exercício múltiplas vezes (ex: circuitos), pois a tabela `training_session_exercises` não possui constraint UNIQUE em `(session_id, exercise_id)`
* **Escopo**: `training_session_exercises`
* **Onde é imposto**: Ausência intencional de UNIQUE constraint na combinação (session_id, exercise_id)
* **Evidência**: `Hb Track - Backend/app/models/session_exercise.py` (docstring confirma "Allows DUPLICATES"); `schema.sql` (sem UNIQUE em session_id+exercise_id)
* **Teste**: Pendente criação

---

## 2) Backlog (não localizadas / não comprovadas)

> Regras sem evidência objetiva no schema/code. Não usar como verdade operacional.

*(Nenhuma invariante pendente no momento.)*

---

## 3) Inativas (implementadas, mas desligadas)

### INV-TRAIN-017 — Cálculo mensal de badges via schedule (1º dia do mês 01:00)

* Legacy ID: INV-TRAIN-I001
* **Status**: INATIVA
* **Enunciado**: job agendado para rodar mensalmente
* **Estado**: **INATIVO** (comentado)
* **Evidência**: `calculate_monthly_badges_task` comentado em `Hb Track - Backend/app/core/celery_app.py:136-139` (**(COMENTADO)**)

---

## 4) Notas operacionais

1. Se uma “Pretendida” virar real (código/constraint/teste), ela deve migrar para **Confirmada** e ganhar evidência objetiva.
2. Se uma “Inativa” for reativada, ela vira **Confirmada** (se a evidência continuar válida) ou permanece **Inativa** se estiver condicionada a flag.
3. Evitar duplicar regras no PRD/TRD: este arquivo é o índice do “o que vale sempre” (e o TRD é o detalhamento técnico com âncoras).

---
