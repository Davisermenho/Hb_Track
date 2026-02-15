## Protocolo Canônico para Testes de Invariantes no Hb Track

---

**Authority Block**

| Propriedade | Valor |
|---|---|
| Authority | Canon (Canonical Protocol) |
| Scope | training/invariants/testing — Padrão obrigatório para testes |
| Last Verified | 2026-02-08 |
| Depends On | [001-ADR-TRAIN-ssot-precedencia.md](../../../ADR/001-ADR-TRAIN-ssot-precedencia.md), INVARIANTS_TRAINING.md, `schema.sql` |
| Produces | Test files following DoD (Definition of Done), validation results |

---

## 1. Objetivo e Autoridade

Este documento define o **Protocolo Canônico** para validação de invariantes no sistema Hb Track. Ele atua como uma "Rule of Law": testes que não seguem este padrão são, por definição, reprovados.

### Princípio "Mapa vs. Território"

1. **Schema (`Hb Track - Backend/docs/_generated/schema.sql`) é o Mapa:** Ele é a **Fonte da Verdade para Requisitos de Setup**. O teste deve consultar o schema para identificar quais colunas são NOT NULL, quais FKs existem e quais Enums são aceitos.
2. **Runtime é o Território:** A prova de uma invariante é a **rejeição explícita** (exceção/erro) pelo motor do banco de dados ou serviço durante a execução.
* *Exceção:* O schema pode ser usado como prova secundária (tripwire) para confirmar bindings (triggers/funções), mas nunca como prova primária de enforcement.

---

## 2. Definition of Done (DoD) Global

Um teste só é considerado "Done" se satisfizer todos os critérios normativos abaixo:

* **DoD-0 (Taxonomia e Nomenclatura):** 
* * Arquivo: 
* * * `tests/invariants/test_inv_train_XXX_<slug>.py` (ex: `test_inv_train_037_cycle_dates.py`).
* * * Classe: TestInvTrainXXX<Slug> (CamelCase, ex: TestInvTrain037CycleDates).
* * * Apenas 1 teste principal por invariante.

* **DoD-1 (Evidência Estável):**
* *Regra Alvo:* Deve apontar a âncora exata (Arquivo + Símbolo/Constraint).
* *Requisitos de Setup:* Devem citar a origem no `Hb Track - Backend/docs/_generated/schema.sql` (Tabela + Coluna + Constraint), não apenas "analisei a tabela".

* **DoD-2 (Prova por Classe):** Segue estritamente a Matriz Canônica (Seção 3).
* **DoD-3 (Anti-Falso-Positivo & Payload Mínimo):** O teste negativo deve provar que falhou pela **invariante alvo** e não por erro de setup.
* *Regra:* O payload deve ser o mínimo necessário para satisfazer todas as outras constraints (FKs, NOT NULLs) da tabela.

* **DoD-4 (Assert Estável):** **Proibido string match em mensagens humanas.**
* *Regra:* `IntegrityError` é necessário mas não suficiente. O assert deve validar:
1. **SQLSTATE** Deve ser extraído do objeto de erro conforme o driver/dialect; o teste deve validar o código canônico do Apêndice A por um atributo estruturado (não por mensagem).
2. **Constraint Name** (Secundário, obrigatório quando exposto pelo driver).

* **DoD-5 (Isolamento de Sessão):** Se o teste causa `IntegrityError`, ele deve garantir a restauração do estado da sessão (via `rollback` ou context manager) para não deixar a conexão inválida para o teardown.
* **DoD-6 (Anti-Colisão):** Proibido usar IDs fixos. Use factories ou `uuid4()`.
* **DoD-6a (Lookup/Seed Tables): Proibido criar linhas em tabelas de catálogo/config (seed).**
Se a tabela for lookup/seed/config (catálogo com IDs semânticos e/ou seed estável — ex.: `categories`), é **proibido** criar novas linhas em testes de invariantes.
  * ✅ Faça: Selecionar um registro existente via SQL/ORM (ex.: `ORDER BY id LIMIT 1`, ou filtro estável como `max_age`, `code`, `name`).
  * ❌ Não faça: `INSERT` / `Factory` / `Model(...)` para criar novas linhas em tabelas de catálogo.
  * Motivo: evita poluição do catálogo e falhas/flakiness por setup (DoD-3).
* **DoD-7 (Sensibilidade):** O teste deve representar a **Mínima Violação Específica**.
* *Critério:* O teste é considerado sensível se: (SQLSTATE bate) AND (Constraint Name bate) AND (Payload é válido para todo o resto).

* **DoD-8 (Fixtures Vinculadas):** Uso de fixtures restrito à necessidade da classe (Seção 3). Padrão do módulo é `async_db`; uso síncrono (`db`) exige justificativa.
* **DoD-9 (Pipeline Aware):** O teste pressupõe que artefatos gerados (`docs/_generated`) estão atualizados.

---

## 3. Matriz Canônica: Classe vs. Prova

| Classe | Descrição | Fixtures Permitidas | Prova Primária (Obrigatória) |
| --- | --- | --- | --- |
| **A** | **DB Constraint** (CHECK, UNIQUE, FK, NOT NULL) | `async_db` | **Runtime Integration**. Rejeição com SQLSTATE correto + Constraint Name. |
| **B** | **DB Trigger / Function** | `async_db` | **Runtime Integration**. Validação de efeito colateral. |
| **C1** | **Service Puro** (Lógica s/ IO) | Nenhuma (Mocks ok) | **Unit Test**. Exception de Negócio. |
| **C2** | **Service com DB** (Depende de Query/Estado) | `async_db` | **Integration Test**. Exception de Negócio (sem mock de DB). |
| **D** | **Router + Auth/RBAC** | `client + auth_client` | **API Test**. Status Code (403/401/200). Evidência requer Router + Permission Guard. |
| **E1** | **Celery Task Pura** | Nenhuma | **Unit Test**. Chamada direta da função. |
| **E2** | **Celery Task com DB** | `async_db` | **Integration Test**. Chamada direta + validação de estado DB. |
| **F** | **OpenAPI Contrato** | Nenhuma (Leitura JSON) | **Contract Test**. Validação de JSON Pointer específico. |

**Nota sobre Classe B (Trigger/Function):**
O verifier aceita dois modos de evidência para Classe B:
- **B1**: anchors `db.table + db.column + db.comment` → valida `COMMENT ON COLUMN` no schema
- **B2** (preferido): anchors `db.table + db.trigger + db.function` → valida binding no schema (CREATE TRIGGER ON table EXECUTE FUNCTION)

Em ambos os modos, a **prova primária continua sendo runtime** (efeito colateral). O schema é apenas evidência secundária (tripwire) para confirmar bindings.

---

## 4. Templates e Formas Mínimas

### Template A: DB Integrity (CHECK/UNIQUE)

**Forma Mínima:**

1. **1 Caso Válido:** Limite do range ou valor padrão.
2. **2 Casos Inválidos (Bordas):** Imediatamente acima/abaixo ou violação direta.
3. **Justificativa de Setup:** Toda entidade criada deve suprir uma FK ou NOT NULL citada no DoD-1. "Over-setup" é proibido.

**Assert Checklist:**

* `pytest.raises(IntegrityError)`
* `assert exc.orig.pgcode == 'CODIGO_DO_APENDICE'`
*  Validar constraint_name via atributo estruturado do erro quando exposto pelo driver/dialect; se não exposto, documentar fallback (SQLSTATE apenas) e justificar por evidência do driver.

### Template D: Router + RBAC

**Evidência Mínima:** Router File + Dependency Guard + Fonte do Mapeamento de Permissão.
**Forma Mínima:**

1. **Sem Auth:** 401.
2. **Auth Incorreto:** 403 (Papel sem permissão).
3. **Auth Correto:** 200/201 (Passou pelo gate de segurança).

### Template F: OpenAPI Contrato

**Âncora de Evidência:** Path + Method + OperationId.
**Pointers Obrigatórios:**

* `/paths/{path}/{method}/operationId`
* `/paths/{path}/{method}/responses/{code}`
* Schema Key relevante (ex: `content/application/json/schema`)
* *Nota:* Validar apenas os campos citados na evidência; não validar o arquivo todo.

---

## 5. Regras Operacionais para Agentes (Obrigatório)

Todo Agente deve emitir o seguinte **Preâmbulo de Planejamento** antes de gerar código. Se não conseguir preencher, deve marcar como PENDING e pedir o schema.

### Obrigação A: Declaração de Requisitos de Inserção (Payload Mínimo)

 "Analisei o `Hb Track - Backend/docs/_generated/schema.sql`. Para criar o payload mínimo, identifico:
  1. **FK Obrigatória:** `organization_id` (Âncora: `training_sessions.organization_id FK`). Usarei fixture `inv_org`.
  2. **NOT NULL:** `status` (Âncora: `training_sessions.status NOT NULL`). Usarei 'draft'.
  3. **Enum:** `session_type` (Âncora: `TYPE session_type`). Usarei 'quadra'.
  O resto será omitido."
 

### Obrigação B: Declaração de Critério de Falha

  "Invariante alvo: `ck_training_session_dates` (CHECK).
  * **SQLSTATE Esperado:** `23514` (check_violation).
  * **Constraint Name:** `ck_training_session_dates`.
  * **Estratégia:** `pytest.raises` validando SQLSTATE e presença do nome da constraint."
  
---

## 6. Gates de Qualidade (Review)

1. **Sensibilidade:** O teste negativo valida simultaneamente SQLSTATE + constraint_name (quando disponível) e o payload é válido para todas as outras constraints. Se qualquer um desses três falhar, é falso positivo.
2. **Estabilidade:** O teste depende de frases como "valor inválido" na mensagem de erro? (Se sim, Reprovado).
3. **Conformidade:** O teste usa `async_db` para contrato OpenAPI? (Se sim, Reprovado).

---

## Apêndice A: Mapeamento Canônico SQLSTATE (Postgres)

| Violação | SQLSTATE (pgcode) | Observação |
| --- | --- | --- |
| **NOT NULL** | `23502` | `not_null_violation` |
| **FOREIGN KEY** | `23503` | `foreign_key_violation` |
| **UNIQUE** | `23505` | `unique_violation` |
| **CHECK** | `23514` | `check_violation` |
| **TRIGGER** | Variável | Depende do `ERRCODE` no `RAISE`. Se genérico, pode ser `P0001`. Validar implementação. |

---

## EXEMPLOS APROVADOS (GOLDEN)

Estes exemplos ilustram o padrão canônico exigido para testes de invariantes. Todo agente deve seguir estritamente estes modelos para as Classes A e F.

**EXEMPLO GOLDEN 1**
Classe A (DB CHECK) com assert estável (sem string match humano)

    import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

@pytest.mark.asyncio
async def test_golden_class_a_check_constraint(async_db):
    """
    Classe: A (DB Constraint - CHECK)
    Prova primária: Runtime (Postgres rejeita)
    Assert estável: SQLSTATE + constraint_name (quando exposto)
    Observação: payload mínimo deve ser derivado do schema.sql (FKs/NOT NULL/enums).
    """

    # 1) Criar payload mínimo válido (tudo certo, exceto o campo alvo)
    obj = YourModel(
        id=uuid4(),
        # ... preencher apenas o necessário para satisfazer FKs e NOT NULL ...
        target_field="VALOR_INVALIDO",  # mínima violação específica
    )
    async_db.add(obj)

    # 2) Execução e captura
    with pytest.raises(IntegrityError) as exc_info:
        await async_db.flush()

    # 3) Assert estável: SQLSTATE (primário)
    orig = exc_info.value.orig
    pgcode = getattr(orig, "pgcode", None)
    assert pgcode == "23514"  # CHECK violation

    # 4) Assert estável: constraint_name (secundário, estruturado quando exposto)
    # (sem depender de str(e))
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None) or getattr(orig, "constraint_name", None)

    # Se o driver expõe, deve bater exatamente. Se não expõe, aplicar fallback documentado.
    if constraint_name is not None:
        assert constraint_name == "NOME_DA_CONSTRAINT_NO_SCHEMA"

    # 5) Isolamento: restaurar sessão após IntegrityError
    await async_db.rollback()


**EXEMPLO GOLDEN 2**
Classe F (OpenAPI Contract) com ponteiros específicos

    import json
from pathlib import Path

def test_golden_class_f_openapi_contract():
    """
    Classe: F (OpenAPI Contrato)
    Prova primária: contract test lendo openapi.json
    Regra: validar apenas os JSON pointers citados na evidência (não o arquivo todo).
    """

    p = Path("docs/_generated/openapi.json")
    assert p.exists()

    spec = json.loads(p.read_text(encoding="utf-8"))

    # Exemplo de âncora: Path + Method + operationId
    path = "/api/v1/SEU-ENDPOINT"
    method = "get"
    op = spec["paths"][path][method]

    assert op["operationId"] == "SEU_OPERATION_ID"

    # Exemplo: response code exigido
    assert "200" in op["responses"]

    # Exemplo: schema key relevante (ajuste conforme evidência)
    content = op["responses"]["200"]["content"]
    assert "application/json" in content

---
