# Guia de Uso: Model Requirements Validator

## Visão Geral

O `model_requirements.py` valida conformidade estrutural entre SQLAlchemy models e `schema.sql` (SSOT), complementando o Alembic compare com validações adicionais que detectam alucinações de IA, tipos incorretos, e violations de constraints.

**Localização:** `Hb Track - Backend/scripts/model_requirements.py`

**Integração:** Executado automaticamente como STEP 4 no `models_autogen_gate.ps1`

---

## Quando usar

### ✅ Usar model_requirements quando:
- Após gerar/modificar models (manualmente ou via autogen)
- Antes de commit (via pre-commit hook)
- Em CI/CD (automático em PRs)
- Para detectar alucinações de IA (coluna extra, tipo errado)
- Após aplicar migrations complexas (validar sincronização)
- Quando Alembic não detecta diferenças mas algo parece errado

### ❌ NÃO usar quando:
- Apenas lendo código (não há necessidade de validação)
- Testando lógica de negócio (use pytest)
- Fazendo consultas SQL diretas (não relacionado)

---

## Uso básico

### Validação isolada (apenas requirements)

```powershell
# Validação padrão (perfil strict)
python "Hb Track - Backend\scripts\model_requirements.py" --table attendance

# Com perfil específico
python "Hb Track - Backend\scripts\model_requirements.py" --table teams --profile fk

# Salvar relatório customizado (se implementado)
python "Hb Track - Backend\scripts\model_requirements.py" --table seasons --report custom_report.json
```

### Validação integrada (gate completo)

```powershell
# Executar todos os gates (guard → parity → requirements)
.\scripts\models_autogen_gate.ps1 -Table "attendance" -Profile "strict"

# Com allowlist para arquivos modificados
.\scripts\models_autogen_gate.ps1 -Table "attendance" -Allow "app/models/attendance.py"

# Perfil relaxado para ciclos FK
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile "fk" -AllowCycleWarning
```

---

## Perfis de validação

### strict (padrão)

**Descrição:** Todas as validações A-H ativadas. Conformidade 100% exigida.

**Quando usar:**
- Models novos (após criação inicial)
- Models estáveis (sem metaprogramming)
- Validação final antes de merge

**Validações incluídas:**
- ✅ A: Colunas exatas (extras/faltantes)
- ✅ B: Tipos corretos (PG ↔ SA)
- ✅ C: Nullable correto (NOT NULL ↔ nullable=False)
- ✅ D: FKs corretas (nome, ref, ondelete, use_alter)
- ✅ E: CHECKs presentes
- ✅ F: Indexes explícitos
- ✅ G: UNIQUE constraints
- ✅ H: Server defaults

**Exemplo:**
```powershell
python scripts\model_requirements.py --table attendance --profile strict
# Exit 0: PASS (100% conforme)
# Exit 4: FAIL (violations detectadas)
```

---

### fk (Foreign Keys apenas)

**Descrição:** Apenas validações A-D (colunas + tipos + nullable + FKs). CHECKs/Indexes/Defaults ignorados.

**Quando usar:**
- Ciclos FK documentados (teams ↔ seasons)
- Models com constraints complexas gerenciadas manualmente
- Validação rápida focada em integridade referencial

**Validações incluídas:**
- ✅ A: Colunas exatas
- ✅ B: Tipos corretos
- ✅ C: Nullable correto
- ✅ D: FKs corretas

**Validações ignoradas:**
- ❌ E-H: CHECKs, Indexes, Uniques, Defaults

**Exemplo:**
```powershell
python scripts\model_requirements.py --table teams --profile fk
# Usado para ciclos FK onde use_alter=True é esperado
```

---

### lenient (Exceções)

**Descrição:** Todas as validações A-H, mas permite exceções definidas em `.hb_guard/model_requirements_exceptions.json`.

**Quando usar:**
- Models com metaprogramming avançado
- Casos especiais documentados (ex: dynamic columns)
- Migrations em andamento (temporário)

**Como funciona:**
1. Executar todas as validações
2. Carregar exceções de `.hb_guard/model_requirements_exceptions.json`
3. Filtrar violations que estão na allowlist
4. Reportar apenas violations não documentadas

**Arquivo de exceções (exemplo):**
```json
{
  "exceptions": [
    {
      "table": "attendance",
      "model_path": "app/models/attendance.py",
      "ignore": ["MISSING_SERVER_DEFAULT"],
      "reason": "Server defaults serão adicionados na migration 0042"
    },
    {
      "table": "teams",
      "ignore": ["INDEX_WHERE_MISMATCH"],
      "reason": "Índice parcial gerenciado manualmente no schema.sql"
    }
  ]
}
```

**Exemplo:**
```powershell
python scripts\model_requirements.py --table attendance --profile lenient
# Output:
# [OK] lenient profile passed
# [INFO] exceptions_loaded=2 applied=1
# [INFO] lenient_exceptions_applied:
#   - MISSING_SERVER_DEFAULT: source | reason=Server defaults migration pending
```

---

## Interpretando violations

### Formato de output

```
[FAIL] model_requirements strict profile violations (table=attendance)
[INFO] model_path=C:\HB TRACK\Hb Track - Backend\app\models\attendance.py
  - VIOLATION_CODE: column_name details model_line=123
  - VIOLATION_CODE: column_name details model_line=456
```

### Códigos de violation

#### A1_EXTRA_COLUMN
**Causa:** Coluna no model que não existe em schema.sql.

**Motivo comum:** Alucinação de IA, copy-paste incorreto.

**Fix:**
```python
# ❌ Remover linha
# extra_field: Mapped[str] = mapped_column(String(100))

# OU criar migration se coluna é legítima
alembic revision --autogenerate -m "add extra_field to attendance"
```

---

#### A2_MISSING_COLUMN
**Causa:** Coluna em schema.sql que falta no model.

**Motivo comum:** Model desatualizado após migration.

**Fix:**
```python
# ✅ Adicionar coluna no model
new_column: Mapped[str] = mapped_column(String(200), nullable=False)
```

---

#### B1_TYPE_MISMATCH
**Causa:** Tipo PG vs SA incompatível.

**Motivo comum:** String usado ao invés de Date/Integer, length incorreto.

**Fix:**
```python
# ❌ ANTES
date: Mapped[str] = mapped_column(String(20))

# ✅ DEPOIS
from datetime import date as date_type
date: Mapped[date_type] = mapped_column(Date, nullable=False)
```

**Mapeamento PG → SA:**
| PostgreSQL | SQLAlchemy |
|------------|------------|
| `integer` | `Integer` |
| `bigint` | `BigInteger` |
| `character varying(N)` | `String(N)` ou `String` |
| `text` | `Text` ou `String` |
| `boolean` | `Boolean` |
| `date` | `Date` |
| `timestamp without time zone` | `DateTime` |
| `timestamp with time zone` | `DateTime(timezone=True)` |
| `uuid` | `Uuid` |
| `numeric(P,S)` | `Numeric(P,S)` |

---

#### C1_NULLABLE_MISMATCH
**Causa:** NOT NULL no DB mas nullable=True no model (ou implícito).

**Motivo comum:** Esquecer de adicionar `nullable=False` em FKs/colunas obrigatórias.

**Fix:**
```python
# ❌ ANTES (nullable implícito = True)
athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id"))

# ✅ DEPOIS
athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id"), nullable=False)
```

---

#### D4_MISSING_USE_ALTER
**Causa:** FK de ciclo sem `use_alter=True`.

**Motivo comum:** Ciclos FK documentados (ex: teams ↔ seasons).

**Fix:**
```python
# ❌ ANTES
season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))

# ✅ DEPOIS (para ciclos FK conhecidos)
season_id: Mapped[int] = mapped_column(
    Integer, 
    ForeignKey("seasons.id", use_alter=True, name="fk_teams_season_id")
)
```

**Ciclos documentados no projeto:**
- `fk_teams_season_id` (teams → seasons)
- `fk_seasons_team_id` (seasons → teams)

---

#### E1_MISSING_CHECK / E2_EXTRA_CHECK
**Causa:** CHECK constraint faltando ou extra no model.

**Fix:**
```python
# ✅ Adicionar no __table_args__
__table_args__ = (
    CheckConstraint("status IN ('active', 'inactive')", name="ck_table_status_valid"),
)
```

---

#### F1_MISSING_INDEX / F2_EXTRA_INDEX
**Causa:** INDEX explícito faltando ou extra.

**Fix:**
```python
# ✅ Adicionar no __table_args__
__table_args__ = (
    Index("idx_attendance_team_date", "team_id", "date"),
)
```

---

#### G1_UNIQUE_DUPLICATE_WITH_INDEX
**Causa:** UNIQUE constraint + Index com unique=True (redundância).

**Fix:**
```python
# ❌ ANTES (redundante)
__table_args__ = (
    UniqueConstraint("email", name="uq_users_email"),
    Index("uq_users_email", "email", unique=True),  # ❌ Duplicado
)

# ✅ DEPOIS (escolher um)
__table_args__ = (
    UniqueConstraint("email", name="uq_users_email"),
    # OU
    # Index("uq_users_email", "email", unique=True),
)
```

---

#### H1_MISSING_SERVER_DEFAULT
**Causa:** Schema.sql tem DEFAULT mas model não tem `server_default`.

**Motivo comum:** Esquecido durante autogen.

**Fix:**
```python
from sqlalchemy import text

# ❌ ANTES
is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

# ✅ DEPOIS
is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

# Para strings:
source: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'manual'"))
```

---

## Exit codes

- **0:** PASS (conformidade total)
- **4:** FAIL (violations detectadas)
- **1:** ERROR (crash interno, bug no script)

**Verificar exit code:**
```powershell
python scripts\model_requirements.py --table attendance
Write-Host "Exit: $LASTEXITCODE"
```

---

## Troubleshooting

### Q: Validator reporta false positive (violation incorreta)?

**A:** Verificar mapeamento PG→SA no código:
1. Abrir `scripts/model_requirements.py`
2. Procurar por `_schema_type_to_key()` e `_model_type_to_key()`
3. Adicionar equivalência se necessário
4. Reportar como bug para review

**Exemplo de equivalência aceitável:**
```python
ACCEPTABLE_EQUIVALENCES: set[tuple[str, str]] = {
    ("varchar|None", "text"),  # String() sem length ≈ Text
    ("text", "varchar|None"),
}
```

---

### Q: Metaprogramming não é suportado?

**A:** Usar perfil `lenient` com exceções documentadas:
```json
{
  "exceptions": [
    {
      "table": "dynamic_table",
      "ignore": ["EXTRA_COLUMN"],
      "reason": "Colunas dinâmicas adicionadas via __init_subclass__"
    }
  ]
}
```

---

### Q: Relatório JSON não é gerado?

**A:** Feature `--report` está planejada mas não implementada na versão atual. Use output console.

---

### Q: Schema.sql está desatualizado?

**A:** Regenerar schema.sql:
```powershell
# Via generate_docs.py
python scripts\generate_docs.py

# Ou pg_dump direto
pg_dump -h localhost -U user -d hb_track_db --schema-only --no-owner --no-privileges > docs\_generated\schema.sql
```

---

### Q: Performance está lenta?

**A:** Validator parseia schema.sql inteiro. Para múltiplas tabelas, considerar:
```powershell
# ❌ Lento (parsing repetido)
foreach ($table in @("attendance", "teams", "seasons")) {
    python scripts\model_requirements.py --table $table
}

# ✅ Rápido (batch via CI/CD ou script custom)
# Implementar cache de parsed schema.sql (feature futura)
```

---

## Integração com CI/CD

### Pre-commit hook (local)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: model-requirements
        name: Model Requirements Validator
        entry: python scripts/model_requirements.py
        language: system
        args: ["--table", "attendance", "--profile", "strict"]
        pass_filenames: false
```

### GitHub Actions (PR validation)

```yaml
# .github/workflows/pr-validation.yml
name: PR Validation
on: [pull_request]
jobs:
  validate-models:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate attendance model
        run: python scripts/model_requirements.py --table attendance --profile strict
      - name: Validate teams model
        run: python scripts/model_requirements.py --table teams --profile fk
```

---

## Boas práticas

### ✅ DO:
- Executar `model_requirements.py` após cada modificação de model
- Usar perfil `strict` como padrão (conformidade total)
- Documentar exceções em `lenient` mode com `reason` claro
- Verificar exit code explicitamente em scripts automatizados
- Manter schema.sql atualizado (regenerar após migrations)

### ❌ DON'T:
- Ignorar violations sem investigar (pode indicar bug sério)
- Usar `lenient` mode como padrão (exceções devem ser justificadas)
- Modificar `ACCEPTABLE_EQUIVALENCES` sem aprovação (pode mascarar bugs)
- Pular validação em PRs (use CI/CD hook obrigatório)

---

## Limitações Conhecidas

### Validação por Arquivo (não por Classe)

**Problema:** O `model_requirements.py` atualmente valida o **arquivo inteiro**, não `__tablename__` específico. Isso causa **falsos positivos** em arquivos multi-class.

**Exemplo concreto:** `person.py` contém 5 classes:
- `Person` (tabela `persons`)
- `PersonAddress` (tabela `person_addresses`)
- `PersonContact` (tabela `person_contacts`)
- `PersonDocument` (tabela `person_documents`)
- `PersonMedia` (tabela `person_media`)

**Comportamento atual:**
```powershell
python scripts\model_requirements.py --table person_addresses --profile strict
# Valida TODAS as colunas de person.py, incluindo Person, PersonContact, etc.
# Se Person tiver uma violation, person_addresses recebe FAIL (mesmo estando correta)
```

**Tabelas afetadas (falsos positivos):**
- `person_addresses`, `person_contacts`, `person_documents`, `person_media`, `persons`
- `users` (arquivo `user.py` pode ter classes auxiliares)

**Workaround atual:** Usar perfil `fk` ou ignorar FAILs dessas tabelas até a correção.

**Correção planejada:** Modificar `model_requirements.py` para:
1. Extrair `__tablename__` de cada classe no arquivo
2. Validar apenas a classe correspondente à `--table` passada
3. Ignorar atributos de outras classes no mesmo arquivo

**Tracking:** Issue pendente para implementação.

---

## Comandos de referência rápida

```powershell
# Validação isolada (strict)
python scripts\model_requirements.py --table attendance --profile strict

# Validação isolada (fk apenas)
python scripts\model_requirements.py --table teams --profile fk

# Validação isolada (lenient com exceções)
python scripts\model_requirements.py --table seasons --profile lenient

# Gate completo (guard + parity + requirements)
.\scripts\models_autogen_gate.ps1 -Table "attendance" -Profile "strict"

# Gate com allowlist
.\scripts\models_autogen_gate.ps1 -Table "attendance" -Allow "app/models/attendance.py"

# Gate para ciclo FK
.\scripts\models_autogen_gate.ps1 -Table "teams" -Profile "fk" -AllowCycleWarning

# Verificar exit code
$LASTEXITCODE
```

---

## Referências

- **ADR:** [013-ADR-MODELS.md](../ADR/013-ADR-MODELS.md)
- **Exit Codes:** [exit_codes.md](exit_codes.md)
- **EXEC_TASK:** [EXEC_TASK_ADR_MODELS_001.md](../execution_tasks/EXEC_TASK_ADR_MODELS_001.md)
- **Source:** `Hb Track - Backend/scripts/model_requirements.py`

---

**Última atualização:** 2026-02-11  
**Responsável:** Tech Lead + AI Assistant  
**Versão:** 1.2
