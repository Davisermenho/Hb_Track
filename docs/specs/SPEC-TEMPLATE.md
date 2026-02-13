## Template canônico para gerar SPEC determinística (PT-BR)

Abaixo está a **TEMPLATE** padrão para a criação de uma SPEC.

> **Regra para o agente:** ele só pode preencher campos marcados como `{{...}}`. Qualquer outro conteúdo é “SSOT” e não pode ser alterado.

````md
# SPEC: {{NOME_DO_SISTEMA_OU_COMPONENTE}}

**Versão:** {{SEMVER}}
**Data:** {{YYYY-MM-DD}}
**Derivado de:** {{ADR_OU_ISSUE}}
**Status:** {{DRAFT|APPROVED|DEPRECATED}}
**Autor:** {{TIME}}
**URI/Path Canônico:** `{{PATH_CANONICO_DA_SPEC}}`

**SSOT (dados/input):**
- `{{PATH_SSOT_1}}`
- `{{PATH_SSOT_2}}`

**Artefatos alvo (bit-a-bit):**
- `{{PATH_ARTEFATO_ALVO_1}}`
- `{{PATH_ARTEFATO_ALVO_2_OPCIONAL}}`

**Definição de Sucesso:** {{DEFINICAO_BINARIA_DE_SUCESSO}}

---

## 0. LINGUAGEM NORMATIVA (RFC 2119) — MUST

As palavras-chave "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY" e "OPTIONAL" neste documento DEVEM ser interpretadas conforme RFC 2119.
Termos ambíguos ("ideal", "geralmente", "tente", "normalmente", "em geral") são PROIBIDOS.

---

## 1. CONTRATO DE DETERMINISMO — MUST

### 1.1 Função Pura — MUST
O processo DEVE ser definido como função pura:

`f({{INPUTS_CANONICOS}}) -> {{ARTEFATOS_ALVO}}`

Se os inputs forem idênticos, os artefatos alvo DEVEM ser bit-a-bit idênticos.

> Se existir timestamp, ele DEVE ser determinístico (por `--timestamp` ou `SOURCE_DATE_EPOCH`) OU o artefato alvo deve ser canonicalizado (definir regra).

### 1.2 Fronteira de Inputs — MUST
Somente inputs explicitamente declarados PODEM influenciar o resultado:

| Input | Tipo | Descrição |
|------|------|-----------|
| {{INPUT_1}} | {{TIPO}} | {{DESC}} |
| {{INPUT_2}} | {{TIPO}} | {{DESC}} |

Qualquer input não declarado (ex: hora do sistema, hostname, locale, rede) MUST NOT afetar os artefatos alvo.

### 1.3 Fail-Fast — MUST
Em erro de infraestrutura (ex: arquivo não encontrado, parse inválido), o processo DEVE abortar imediatamente e emitir:
- exit code ≠ 0
- motivo explícito
- localização (arquivo:linha) quando aplicável

Violations de requisitos DEVEM ser coletadas integralmente antes de emitir o exit code de “requirements fail”.

---

## 2. COMPONENTES NORMATIVOS — MUST

### 2.1 Checker (SSOT executor) — MUST
**Checker:** `{{CAMINHO_DO_CHECKER}}`

Todo REQ-XX DEVE possuir um comando verificável que retorne exit code.

### 2.2 Contrato de CLI do Checker — MUST
```bash
{{COMANDO_BASE}} [OPTIONS]
````

**OPTIONS (MUST documentar defaults):**

* {{FLAG_1}}
* {{FLAG_2}}

### 2.3 Exit Codes do Checker — MUST (estáveis; mudam só em MAJOR)

| Code  | Semântica  | Descrição             |
| ----- | ---------- | --------------------- |
| 0     | PASS       | {{CONDICAO_PASS}}     |
| {{X}} | REQ_FAIL   | {{CONDICAO_REQ_FAIL}} |
| 1     | TOOL_ERROR | Crash/infra           |

**Regra MUST:** `REQ_FAIL` ocorre somente quando houver violation severity=ERROR (se aplicável).

---

## 3. MANIFESTS (INPUTS + ENV) — MUST

### 3.1 Inputs Manifest — MUST

**Path:** `{{PATH_INPUTS_MANIFEST}}`

DEVE conter no mínimo:

* cada input com `path` + `sha256` (quando arquivo)
* valores escalares (ex.: profile)

### 3.2 Environment Manifest — MUST

**Path:** `{{PATH_ENV_MANIFEST}}`

DEVE conter no mínimo:

* runtime (ex: `python@3.11.x`)
* dependências (ou lockfiles + hashes)
* `generatedBy`: `{{TOOL}}@{{VERSION}}`

---

## 4. FORMATO OBRIGATÓRIO DE REQUISITO (MÁQUINA-A-MÁQUINA) — MUST

Cada requisito REQ-XX DEVE seguir este template (campos obrigatórios):

* **ID:** `REQ-XX`
* **Norma:** `MUST | MUST NOT | SHOULD`
* **Descrição curta:** (1 linha)
* **Como validar (comando):** (1 comando/script que retorne exit code)
* **Critério PASS:** (expressão binária)
* **Critério FAIL:** (expressão binária)
* **Evidência gerada:** (path determinístico)
* **Escopo:** `ALL | CI | LOCAL | RELEASE`

---

## 5. CATÁLOGO DE REQUISITOS (REQ-01..REQ-N)

### REQ-01: {{NOME}}

* **ID:** REQ-01
* **Norma:** MUST
* **Descrição curta:** {{...}}
* **Como validar:** `{{...}}`
* **Critério PASS:** `{{...}}`
* **Critério FAIL:** `{{...}}`
* **Evidência gerada:** `%TEMP%/hb_spec_runs/{run_id}/spec_REQ-01.json`
* **Escopo:** ALL

> Repita até REQ-N (N deve ser explícito e fechado).

---

## 6. EVIDÊNCIAS (FORMATO) — MUST

### 6.1 Run ID determinístico — MUST

`run_id = sha256(spec_version + inputs_manifest_sha256 + env_manifest_sha256 + {{PARAMETROS_RELEVANTES}})`

### 6.2 Evidência por requisito — MUST

Cada REQ-XX DEVE gerar:
`%TEMP%/hb_spec_runs/{run_id}/spec_REQ-XX.json`

### 6.3 JSON mínimo — MUST

```json
{
  "spec_id": "{{SPEC_ID}}",
  "spec_version": "{{SEMVER}}",
  "req_id": "REQ-01",
  "run_id": "<sha256>",
  "status": "PASS|FAIL|ERROR",
  "exit_code": 0,
  "fail_reason": null,
  "inputs_manifest_sha256": "<sha256>",
  "env_manifest_sha256": "<sha256>",
  "artefatos_alvo": [
    {"path": "{{ARTEFATO}}", "sha256": "<sha256>"}
  ],
  "notes": []
}
```

---

## 7. TABELA FINAL DE VERIFICAÇÃO — MUST

| ID     | Requisito | Como validar (comando) | Critério PASS | Evidência gerada                                |
| ------ | --------- | ---------------------- | ------------- | ----------------------------------------------- |
| REQ-01 | {{...}}   | `{{...}}`              | `{{...}}`     | `%TEMP%/hb_spec_runs/{run_id}/spec_REQ-01.json` |

---

## 8. ANTI-PATTERNS (PROIBIÇÕES EXPLÍCITAS) — MUST

Esta SPEC DEVE ser rejeitada se permitir:

1. Best-effort em erro de infra
2. Silent fail (exit=0 com ERRORs)
3. Host leak (hostname/username/path absoluto/etc.)
4. Ordenação implícita (sem sort explícito)
5. Acesso à rede (se proibido)
6. Pipelines que corrompem exit code (se integrar PS/bash)

---

## 9. CHANGELOG

| Versão  | Data    | Mudanças |
| ------- | ------- | -------- |
| {{...}} | {{...}} | {{...}}  |

---

**FIM DA SPEC**

