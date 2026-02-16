# TEMPLATE — Adoção Organizacional de Documentação Determinística

**Status:** RFC/Playbook  
**Version:** 1.0  
**Date:** 2026-02-16

---

## 1️⃣ Executive Summary

**Objetivo:**
Adotar um modelo de documentação determinística com integridade verificável para:

- Reduzir alucinação de IA
- Eliminar drift documental
- Garantir reprodutibilidade de contratos
- Melhorar confiabilidade de engenharia

**Base técnica:**
Modelo B — Derived Promoted to SSOT with Integrity Manifest

**Status atual:**
Implementado e validado em projeto piloto (HB Track).

---

## 2️⃣ Problema que estamos resolvendo

### Sintomas organizacionais comuns

| Sintoma | Impacto |
|---------|---------|
| Documentação divergente do código | Bugs de integração |
| Discussões sobre "qual é a verdade" | Perda de tempo |
| IA gerando diffs incorretos | Confiabilidade reduzida |
| Regressões silenciosas em contratos | Instabilidade |

---

## 3️⃣ O Modelo Proposto

### Princípio central

> Documentação como sistema determinístico, não narrativa.

### Componentes do modelo

| Componente | Função |
|------------|--------|
| Writer único | Fonte de geração controlada |
| SSOT promovido | Artefatos derivados tratados como verdade |
| Manifest de integridade | Checksums criptográficos |
| Gates automáticos | Validação independente |

---

## 4️⃣ Escopo da Adoção

### Inclui

- Artefatos contratuais (OpenAPI, schema, manifests)
- Documentação técnica canônica
- Saídas geradas por tooling

### Não inclui (inicialmente)

- Documentação de marketing
- Tutoriais livres
- Docs experimentais

---

## 5️⃣ Benefícios Esperados

### Técnicos
- Integridade criptográfica de contratos
- Reprodutibilidade total
- Menos drift estrutural

### Organizacionais
- Menos discussões subjetivas
- IA mais confiável
- Onboarding mais rápido

### Estratégicos
- Base para automação avançada
- Compliance-ready
- Escalabilidade de engenharia

---

## 6️⃣ Requisitos Técnicos

### Mínimos por repositório

- Writer command único
- Integrity manifest
- Gate L0–L2 ativo
- Baseline versionado

### Estrutura padrão

```
docs/_canon/
docs/_ssot/
docs/_generated/
scripts/checks/
```

---

## 7️⃣ Plano de Rollout

### Fase 1 — Piloto (1–2 repos)
- Implementar Modelo B
- Medir fricção
- Ajustar tooling

### Fase 2 — Expansão controlada
- 3–5 repos críticos
- Templates compartilhados
- Hooks padronizados

### Fase 3 — Padronização
- CI required checks
- Guia oficial de engenharia
- Treinamento interno

---

## 8️⃣ Papéis e Responsabilidades

| Papel | Responsabilidade |
|-------|------------------|
| Platform/Infra | Manter templates, evoluir validators |
| Times de produto | Aplicar modelo, manter writer commands |
| Tech Leads | Garantir baseline congelado, aprovar evoluções |

---

## 9️⃣ Política de Versionamento

### Baselines

- docs-determinism-v1
- docs-determinism-v2 (quando evoluir)

### Regra

> Nunca quebrar baseline sem nova versão.

---

## 🔟 Gates Organizacionais

### Required checks (mínimo)

- Determinism gate (L0–L2)

### Opcional (futuro)

- Baseline drift detector
- Evidence gate (L3)

---

## 1️⃣1️⃣ Métricas de Sucesso

### Curto prazo
- Redução de drift em PRs
- Menos conflitos semânticos

### Médio prazo
- Menos bugs de contrato
- IA mais assertiva

### Longo prazo
- Padronização organizacional
- Aceleração de delivery

---

## 1️⃣2️⃣ Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Resistência cultural | Pilotos pequenos |
| Overhead percebido | Automação forte |
| Overengineering | L0–L2 apenas no início |

---

## 1️⃣3️⃣ Playbook de Adoção por Repositório

Checklist rápido:

- [ ] Definir writer único
- [ ] Criar manifest de integridade
- [ ] Implementar gate L0–L2
- [ ] Congelar baseline
- [ ] Adicionar hook/CI

**Tempo típico:** 2–6 horas por repo.

---

## 1️⃣4️⃣ Quando NÃO adotar

- Projetos descartáveis
- Repos de protótipo
- Documentação puramente narrativa

---

## 1️⃣5️⃣ Roadmap Futuro

Possíveis evoluções:

- L3 Evidence determinism
- Runtime reproducibility
- Universal Doc System (UDS)
- Tooling open-source

---

## 1️⃣6️⃣ FAQ Interno

**Isso substitui docs-as-code?**
Não. É uma evolução.

**Isso é só para IA?**
Não. IA é beneficiária, não motivação única.

**É pesado?**
Não após baseline.

**Pode ser removido?**
Sim, via baseline versioning.

---

## 1️⃣7️⃣ Contato / Ownership

- **Owner:** Plataforma / Arquitetura
- **Maintainers:** Guilda de Engenharia
- **Canal:** #deterministic-docs

---

## 🧩 Anexos

| Recurso | Localização |
|---------|-------------|
| SPEC Modelo B | `docs/_canon/SPECS/SPEC_MODEL_B_DERIVED_PROMOTED_SSOT.md` |
| Exemplo de baseline | `docs/_canon/BASELINES/docs-determinism-v1.md` |
| Guia "how we built" | `docs/guides/how_we_built_deterministic_docs.md` |
| Gate validator | `scripts/checks/check_hb_track_profile.py` |

---

## Referências

- Baseline: `docs/_canon/BASELINES/docs-determinism-v1.md`
- SPEC: `docs/_canon/SPECS/SPEC_MODEL_B_DERIVED_PROMOTED_SSOT.md`
- Status: `docs/_canon/STATUS/docs_determinism_status.md`
- Writer: `docs/_ssot/update_gen.ps1`

---

*Este documento faz parte do sistema de governança de documentação do HB Track.*
