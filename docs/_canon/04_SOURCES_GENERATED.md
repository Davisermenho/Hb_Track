# Arquivos Gerados: Função & Uso

Estes arquivos são **derivados** de SSOT (schema.sql, código, ADRs). Consulte para validação; **não edite manualmente**.

---

## Tabela de Referência

| Arquivo | Função | Use Para | Como Regenerar |
|---------|--------|----------|-----------------|
| `schema.sql` | Constraints, triggers, defaults reais do BD | Debugar divergências DB vs model; validar tipos | `powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\inv.ps1" refresh` (ver `docs/_canon/05_MODELS_PIPELINE.md`) |
| `openapi.json` | Contratos API (schemas, operationIds, parâmetros) | Validar endpoints, verificar breaking changes | `powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\inv.ps1" refresh` |
| `alembic_state.txt` | Estado atual de migrações rodadas | Verificar qual versão está deploy; auditar histórico | `powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\inv.ps1" refresh` |
| `parity_report.json` | Divergências model ↔ schema | Detectar conflicts antes de merge | Executar parity scanner (ver EXEC_TASK_ADR_MODELS_001.md) |
| `manifest.json` | Índice de todos arquivos commitados + hash | Auditar integridade, rastrear versão | Gerado por build process |
| `trd_training_permissions_report.txt` | Análise de permissões no módulo training | Validar RBAC, auditoria de acesso | Script em docs/scripts/ ou via agent |
| `trd_training_openapi_operationIds.txt` | Lista de operationIds training | Rastrear endpoints training disponíveis | Customization de openapi.json |

---

## Quando Regenerar

- **Sempre que:** mudar models/migrations/endpoints e precisar atualizar artefatos gerados (`schema.sql`, `openapi.json`, `alembic_state.txt`)
- **Teste:** regenerate → integre no CI/CD (pull sempre antes de merge)
- **Dúvida:** vá para `docs/ADR/001-ADR-TRAIN-ssot-precedencia.md` (SSOT wins)

---

## Path Completo

Artefatos canônicos: `docs/_generated/` (repo root).

Mirror de execução (gerado pelo backend e copiado para o repo root): `Hb Track - Backend/docs/_generated/`.

Acesso direto via `docs/_generated/schema.sql`, etc.
