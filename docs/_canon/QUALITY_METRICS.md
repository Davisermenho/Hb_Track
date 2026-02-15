# HB Track - Documentação de Qualidade de Código

## QUALITY_METRICS.md

**O Manual de Ética do Código**  
*Define o orçamento (budget) de complexidade permitido no código*

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Princípios Fundamentais](#princípios-fundamentais)
3. [Métricas de Qualidade](#métricas-de-qualidade)
4. [Padrões de Implementação](#padrões-de-implementação)
5. [Segurança](#segurança)
6. [Prevenção de Gaps e Erros](#prevenção-de-gaps-e-erros)
7. [Processo de Validação](#processo-de-validação)

---

## 🎯 Visão Geral

Este documento estabelece os padrões de qualidade, segurança e manutenibilidade para o sistema HB Track. Todos os componentes do sistema devem aderir a estes padrões para garantir código robusto, seguro e sustentável.

### Objetivos

- ✅ Reduzir bugs e vulnerabilidades em produção
- ✅ Facilitar manutenção e evolução do código
- ✅ Garantir consistência em toda a base de código
- ✅ Otimizar performance e escalabilidade
- ✅ Proteger dados sensíveis de atletas e organizações

---

## 🏛️ Princípios Fundamentais

### 1. **Legibilidade**
> *"Código é lido 10x mais vezes do que escrito"*

- Nome de variáveis/funções devem ser autoexplicativos
- Evitar abreviações obscuras
- Usar português para domínio de negócio, inglês para código técnico

**❌ Ruim:**
```python
def proc_atl(d, t):
    if d['st'] == 'A' and t.cap > len(t.atl):
        return True
    return False
```

**✅ Bom:**
```python
def pode_adicionar_atleta(dados_atleta: dict, time: Team) -> bool:
    """Verifica se um atleta pode ser adicionado ao time."""
    atleta_ativo = dados_atleta['status'] == 'ATIVO'
    time_tem_vaga = time.capacidade_maxima > len(time.atletas)
    
    return atleta_ativo and time_tem_vaga
```

### 2. **Simplicidade**
> *"A solução mais simples que funciona é a solução mais apropriada"*

- Evitar over-engineering
- Uma função = uma responsabilidade
- Preferir composição a herança complexa

### 3. **Testabilidade**
> *"Se é difícil testar, está mal projetado"*

- Injeção de dependências
- Funções puras quando possível
- Mocks para dependências externas

### 4. **Manutenibilidade**
> *"Código que muda junto, fica junto"*

- Alta coesão dentro de módulos
- Baixo acoplamento entre módulos
- Documentação clara de decisões arquiteturais (ADRs)

---

## 📊 Métricas de Qualidade

### 1. Complexidade Ciclomática

**Definição:** Número de caminhos independentes através do código  
**Limite:** ≤ 6

**❌ Ruim (Violando):**
```python
def calcular_pontuacao_partida(jogador: Jogador, partida: Partida) -> int:
    pontos = 0
    
    if jogador.posicao == "GOLEIRO":
        if partida.gols_sofridos == 0:
            pontos += 10
            if partida.defesas > 15:
                pontos += 5
                if partida.tempo_jogado > 50:
                    pontos += 3
        else:
            if partida.defesas > 10:
                pontos += 3
                if partida.gols_sofridos < 15:
                    pontos += 2
    elif jogador.posicao == "PONTA":
        if partida.gols > 5:
            pontos += 15
            if partida.assistencias > 3:
                pontos += 8
        else:
            if partida.gols > 2:
                pontos += 8
    # ... mais 20 linhas de ifs aninhados
    
    return pontos
```
*Complexidade: ~15 (CRÍTICO)*

**✅ Bom (Corrigido):**
```python
class CalculadoraPontuacao:
    """Calcula pontuação de jogadores usando estratégias por posição."""
    
    ESTRATEGIAS = {
        "GOLEIRO": "_calcular_pontos_goleiro",
        "PONTA": "_calcular_pontos_ponta",
        "ARMADOR": "_calcular_pontos_armador",
        "PIVÔ": "_calcular_pontos_pivo",
    }
    
    def calcular(self, jogador: Jogador, partida: Partida) -> int:
        estrategia = self.ESTRATEGIAS.get(jogador.posicao)
        if not estrategia:
            raise ValueError(f"Posição inválida: {jogador.posicao}")
        
        metodo = getattr(self, estrategia)
        return metodo(jogador, partida)
    
    def _calcular_pontos_goleiro(self, jogador: Jogador, partida: Partida) -> int:
        """Calcula pontos para goleiros (CC: 3)."""
        pontos_base = self._pontos_defesas(partida)
        bonus_clean_sheet = 10 if partida.gols_sofridos == 0 else 0
        bonus_tempo = 3 if partida.tempo_jogado > 50 else 0
        
        return pontos_base + bonus_clean_sheet + bonus_tempo
    
    def _pontos_defesas(self, partida: Partida) -> int:
        """Calcula pontos por defesas (CC: 2)."""
        if partida.defesas > 15:
            return 5
        elif partida.defesas > 10:
            return 3
        return 0
    
    # ... métodos similares para outras posições
```
*Complexidade por método: ≤ 3 (ÓTIMO)*

### 2. Profundidade de Aninhamento

**Limite:** ≤ 3 níveis

**❌ Ruim:**
```python
def validar_inscricao_campeonato(atleta, time, campeonato):
    if atleta.ativo:
        if time.ativo:
            if campeonato.aberto:
                if atleta.idade >= campeonato.idade_minima:
                    if atleta.idade <= campeonato.idade_maxima:
                        if not atleta.suspenso:
                            return True
    return False
```

**✅ Bom (Guard Clauses):**
```python
def validar_inscricao_campeonato(
    atleta: Atleta, 
    time: Team, 
    campeonato: Campeonato
) -> bool:
    """Valida se atleta pode ser inscrito no campeonato."""
    
    # Guard clauses - falhas rápidas
    if not atleta.ativo:
        return False
    
    if not time.ativo:
        return False
    
    if not campeonato.aberto:
        return False
    
    if atleta.suspenso:
        return False
    
    # Validação de idade
    idade_valida = (
        campeonato.idade_minima <= atleta.idade <= campeonato.idade_maxima
    )
    
    return idade_valida
```

### 3. Tamanho de Função/Método

**Limite:** ≤ 50 linhas (recomendado: 20-30)

**Estratégias:**
- Extrair submétodos
- Usar objetos de parâmetros
- Aplicar padrão Strategy/Command

### 4. Número de Parâmetros

**Limite:** ≤ 4 parâmetros

**❌ Ruim:**
```python
def criar_atleta(nome, sobrenome, data_nascimento, cpf, rg, email, 
                 telefone, endereco, cidade, estado, cep, time_id, 
                 posicao, numero_camisa):
    pass
```

**✅ Bom:**
```python
@dataclass
class DadosAtleta:
    """Dados para criação de atleta."""
    nome: str
    sobrenome: str
    data_nascimento: date
    cpf: str
    contato: ContatoAtleta
    endereco: EnderecoAtleta
    dados_esportivos: DadosEsportivos

def criar_atleta(dados: DadosAtleta, time_id: int) -> Atleta:
    """Cria novo atleta no sistema."""
    pass
```

### 5. Cobertura de Testes

**Limites:**
- Código crítico (autenticação, pagamentos, pontuação): ≥ 95%
- Lógica de negócio: ≥ 85%
- Código geral: ≥ 75%

**Obrigatório:**
- Testes unitários para regras de negócio
- Testes de integração para APIs
- Testes end-to-end para fluxos críticos

### 6. Duplicação de Código

**Limite:** ≤ 3% de código duplicado

**Estratégias:**
- Extrair funções utilitárias
- Criar classes base
- Usar mixins/composição

### 7. Acoplamento (Coupling)

**Métrica:** Acoplamento Aferente (Ca) e Eferente (Ce)

**❌ Ruim (Alto Acoplamento):**
```python
# module_a.py
from module_b import ClasseB
from module_c import ClasseC
from module_d import ClasseD
from module_e import ClasseE
from module_f import ClasseF

class MinhaClasse:
    def __init__(self):
        self.b = ClasseB()
        self.c = ClasseC()
        self.d = ClasseD()
        self.e = ClasseE()
        self.f = ClasseF()
```

**✅ Bom (Baixo Acoplamento via DI):**
```python
# module_a.py
from typing import Protocol

class RepositorioAtletas(Protocol):
    def buscar(self, id: int) -> Atleta: ...
    def salvar(self, atleta: Atleta) -> None: ...

class ServicoAtleta:
    def __init__(self, repositorio: RepositorioAtletas):
        self._repo = repositorio  # Depende de interface, não implementação
```

### 8. Coesão

**Métrica:** LCOM (Lack of Cohesion of Methods)

**❌ Ruim (Baixa Coesão):**
```python
class GerenciadorGeral:
    """Classe faz muita coisa não relacionada."""
    
    def criar_atleta(self): pass
    def enviar_email(self): pass
    def gerar_relatorio_financeiro(self): pass
    def calcular_estatisticas_partida(self): pass
    def processar_pagamento(self): pass
```

**✅ Bom (Alta Coesão):**
```python
class RepositorioAtleta:
    """Responsável apenas por persistência de atletas."""
    def criar(self, atleta: Atleta) -> Atleta: pass
    def buscar(self, id: int) -> Atleta: pass
    def atualizar(self, atleta: Atleta) -> Atleta: pass
    def deletar(self, id: int) -> None: pass

class ServicoEmail:
    """Responsável apenas por envio de emails."""
    def enviar_boas_vindas(self, destinatario: str): pass
    def enviar_confirmacao(self, destinatario: str): pass
```

---

## 🛡️ Segurança

### 1. Validação de Entrada

**Regra:** NUNCA confie em dados externos

**❌ Ruim:**
```python
@app.post("/atletas")
def criar_atleta(data: dict):
    # SQL Injection vulnerability!
    query = f"INSERT INTO atletas (nome) VALUES ('{data['nome']}')"
    db.execute(query)
```

**✅ Bom:**
```python
from pydantic import BaseModel, Field, validator

class CriarAtletaRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    cpf: str = Field(..., regex=r'^\d{11}$')
    data_nascimento: date
    
    @validator('cpf')
    def validar_cpf(cls, v):
        if not cpf_valido(v):
            raise ValueError('CPF inválido')
        return v

@app.post("/atletas")
def criar_atleta(data: CriarAtletaRequest, db: Session = Depends(get_db)):
    # Protegido por Pydantic + SQLAlchemy ORM
    atleta = Atleta(**data.dict())
    db.add(atleta)
    db.commit()
```

### 2. Autenticação e Autorização

**Checklist:**
- ✅ Senhas com hash bcrypt (min. 10 rounds)
- ✅ Tokens JWT com expiração curta (15-30 min)
- ✅ Refresh tokens em httpOnly cookies
- ✅ Rate limiting em endpoints sensíveis
- ✅ Validação de permissões em TODAS as operações

**❌ Ruim:**
```python
@app.get("/atletas/{atleta_id}")
def obter_atleta(atleta_id: int):
    # Qualquer um pode ver qualquer atleta!
    return db.query(Atleta).get(atleta_id)
```

**✅ Bom:**
```python
@app.get("/atletas/{atleta_id}")
def obter_atleta(
    atleta_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    atleta = db.query(Atleta).get(atleta_id)
    
    if not atleta:
        raise HTTPException(404, "Atleta não encontrado")
    
    # Verificar permissões hierárquicas
    if not current_user.pode_visualizar_atleta(atleta):
        raise HTTPException(403, "Sem permissão para visualizar este atleta")
    
    return atleta
```

### 3. Proteção de Dados Sensíveis

**Dados Sensíveis no HB Track:**
- CPF/RG
- Dados médicos/lesões
- Dados financeiros
- Informações de contato pessoal

**Estratégias:**
- Criptografia em repouso (database encryption)
- Criptografia em trânsito (HTTPS obrigatório)
- Mascaramento em logs
- LGPD compliance (consentimento, direito ao esquecimento)

**❌ Ruim:**
```python
logger.info(f"Atleta criado: {atleta.nome} - CPF: {atleta.cpf}")
# CPF exposto em logs!
```

**✅ Bom:**
```python
logger.info(
    f"Atleta criado: {atleta.nome} - CPF: {mascarar_cpf(atleta.cpf)}",
    extra={"atleta_id": atleta.id}
)
# Output: "Atleta criado: João Silva - CPF: ***.456.789-**"
```

### 4. Proteção contra Ataques Comuns

| Ataque | Mitigação |
|--------|-----------|
| **SQL Injection** | ORM (SQLAlchemy), prepared statements |
| **XSS** | Sanitização de input, Content Security Policy |
| **CSRF** | Tokens CSRF, SameSite cookies |
| **Timing Attacks** | Comparação constante de tempo para senhas/tokens |
| **DDoS** | Rate limiting, CAPTCHA, CDN |
| **Directory Traversal** | Validação de paths, whitelist de arquivos |

---

## 🚨 Prevenção de Gaps e Erros

### 1. Validação em Camadas

**Estratégia de Defesa em Profundidade:**

```
┌─────────────────────────────────────┐
│ 1. Frontend (UI Validation)         │ ← UX imediata
├─────────────────────────────────────┤
│ 2. API Schema (Pydantic)            │ ← Tipagem + validação
├─────────────────────────────────────┤
│ 3. Business Rules (Service Layer)   │ ← Regras de negócio
├─────────────────────────────────────┤
│ 4. Database Constraints (PostgreSQL)│ ← Integridade final
└─────────────────────────────────────┘
```

**Exemplo Completo:**

```python
# 2. API Schema (Pydantic)
class CriarTimeRequest(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    categoria: str = Field(..., regex=r'^(SUB-\d{2}|ADULTO)$')
    temporada_id: int = Field(..., gt=0)
    capacidade_maxima: int = Field(default=18, ge=12, le=30)
    
    @validator('nome')
    def validar_nome_unico(cls, v, values):
        # Validação básica aqui, validação completa no service
        if not v.strip():
            raise ValueError('Nome não pode ser vazio')
        return v.strip()

# 3. Business Rules (Service Layer)
class ServicoTime:
    def criar_time(
        self, 
        dados: CriarTimeRequest, 
        organizacao_id: int,
        db: Session
    ) -> Team:
        """Cria time com validações de negócio."""
        
        # Validar temporada existe e está ativa
        temporada = db.query(Season).get(dados.temporada_id)
        if not temporada:
            raise ValidacaoError("Temporada não encontrada")
        if not temporada.ativa:
            raise ValidacaoError("Temporada não está ativa")
        
        # Validar nome único dentro da organização
        time_existente = db.query(Team).filter(
            Team.nome == dados.nome,
            Team.organizacao_id == organizacao_id
        ).first()
        
        if time_existente:
            raise ValidacaoError(
                f"Já existe um time com nome '{dados.nome}' nesta organização"
            )
        
        # Validar categoria compatível com temporada
        if not self._categoria_compativel(dados.categoria, temporada):
            raise ValidacaoError(
                f"Categoria {dados.categoria} incompatível com temporada"
            )
        
        # Criar time
        time = Team(
            nome=dados.nome,
            categoria=dados.categoria,
            temporada_id=dados.temporada_id,
            organizacao_id=organizacao_id,
            capacidade_maxima=dados.capacidade_maxima
        )
        
        db.add(time)
        db.flush()  # Para obter ID antes do commit
        
        # Auditoria
        self._registrar_auditoria(
            acao="TIME_CRIADO",
            entidade="Team",
            entidade_id=time.id,
            detalhes=dados.dict()
        )
        
        return time

# 4. Database Constraints (Models)
class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    categoria = Column(String(20), nullable=False)
    temporada_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    organizacao_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    capacidade_maxima = Column(Integer, CheckConstraint('capacidade_maxima BETWEEN 12 AND 30'))
    
    __table_args__ = (
        UniqueConstraint('nome', 'organizacao_id', name='uq_team_nome_org'),
        Index('ix_team_temporada', 'temporada_id'),
    )
```

### 2. Tratamento de Erros Robusto

**Hierarquia de Exceções Customizadas:**

```python
# core/exceptions.py
class HBTrackException(Exception):
    """Exceção base do HB Track."""
    codigo: str
    mensagem: str
    http_status: int = 500
    
    def to_dict(self):
        return {
            "codigo": self.codigo,
            "mensagem": self.mensagem,
            "detalhes": getattr(self, 'detalhes', None)
        }

class ValidacaoError(HBTrackException):
    """Erro de validação de dados."""
    http_status = 400
    codigo = "VALIDACAO_FALHOU"

class PermissaoNegadaError(HBTrackException):
    """Usuário não tem permissão."""
    http_status = 403
    codigo = "PERMISSAO_NEGADA"

class RecursoNaoEncontradoError(HBTrackException):
    """Recurso não existe."""
    http_status = 404
    codigo = "RECURSO_NAO_ENCONTRADO"

class RegraDeNegocioError(HBTrackException):
    """Violação de regra de negócio."""
    http_status = 422
    codigo = "REGRA_NEGOCIO_VIOLADA"

# Exemplo de uso
def adicionar_atleta_ao_time(atleta_id: int, time_id: int, db: Session):
    atleta = db.query(Atleta).get(atleta_id)
    if not atleta:
        raise RecursoNaoEncontradoError(f"Atleta {atleta_id} não encontrado")
    
    time = db.query(Team).get(time_id)
    if not time:
        raise RecursoNaoEncontradoError(f"Time {time_id} não encontrado")
    
    if len(time.atletas) >= time.capacidade_maxima:
        raise RegraDeNegocioError(
            f"Time já atingiu capacidade máxima de {time.capacidade_maxima} atletas",
            detalhes={"time_id": time_id, "capacidade": time.capacidade_maxima}
        )
    
    time.atletas.append(atleta)
```

### 3. Logging e Monitoramento

**Níveis de Log:**

```python
import structlog

logger = structlog.get_logger()

# DEBUG: Informações detalhadas para debugging
logger.debug("Buscando atleta", atleta_id=123, filtros={"ativo": True})

# INFO: Eventos importantes do sistema
logger.info("Atleta criado com sucesso", atleta_id=456, nome="João Silva")

# WARNING: Situações inesperadas mas recuperáveis
logger.warning(
    "Tentativa de adicionar atleta a time cheio",
    atleta_id=789,
    time_id=10,
    capacidade_atual=18
)

# ERROR: Erros que afetam operação específica
logger.error(
    "Falha ao processar pagamento",
    atleta_id=123,
    erro=str(e),
    exc_info=True
)

# CRITICAL: Erros que afetam sistema inteiro
logger.critical(
    "Falha de conexão com banco de dados",
    tentativas=5,
    exc_info=True
)
```

**O que NÃO logar:**
- ❌ Senhas (mesmo hasheadas)
- ❌ Tokens completos
- ❌ CPF/RG completos
- ❌ Dados médicos
- ❌ Informações de cartão de crédito

### 4. Testes Abrangentes

**Pirâmide de Testes:**

```
        /\
       /  \      E2E (5%)
      /────\     
     /      \    Integration (15%)
    /────────\   
   /          \  Unit (80%)
  /────────────\
```

**Exemplo - Teste Unitário:**
```python
# tests/unit/services/test_servico_time.py
import pytest
from app.services.time import ServicoTime
from app.exceptions import ValidacaoError, RegraDeNegocioError

class TestServicoTime:
    """Testes unitários para ServicoTime."""
    
    def test_criar_time_com_dados_validos(self, db_session, temporada_ativa):
        # Arrange
        servico = ServicoTime()
        dados = CriarTimeRequest(
            nome="Juvenil A",
            categoria="SUB-16",
            temporada_id=temporada_ativa.id,
            capacidade_maxima=18
        )
        
        # Act
        time = servico.criar_time(dados, organizacao_id=1, db=db_session)
        
        # Assert
        assert time.id is not None
        assert time.nome == "Juvenil A"
        assert time.categoria == "SUB-16"
        assert len(time.atletas) == 0
    
    def test_criar_time_com_nome_duplicado_deve_falhar(
        self, 
        db_session, 
        temporada_ativa,
        time_existente
    ):
        # Arrange
        servico = ServicoTime()
        dados = CriarTimeRequest(
            nome=time_existente.nome,  # Nome já existe
            categoria="SUB-16",
            temporada_id=temporada_ativa.id
        )
        
        # Act & Assert
        with pytest.raises(ValidacaoError, match="Já existe um time"):
            servico.criar_time(dados, organizacao_id=1, db=db_session)
    
    def test_criar_time_em_temporada_inativa_deve_falhar(
        self, 
        db_session, 
        temporada_inativa
    ):
        # Arrange
        servico = ServicoTime()
        dados = CriarTimeRequest(
            nome="Time Teste",
            categoria="SUB-16",
            temporada_id=temporada_inativa.id
        )
        
        # Act & Assert
        with pytest.raises(ValidacaoError, match="Temporada não está ativa"):
            servico.criar_time(dados, organizacao_id=1, db=db_session)
```

**Exemplo - Teste de Integração:**
```python
# tests/integration/test_api_times.py
import pytest
from fastapi.testclient import TestClient

class TestTimesAPI:
    """Testes de integração para API de times."""
    
    def test_criar_time_via_api(
        self, 
        client: TestClient, 
        token_coordenador: str,
        temporada_ativa_id: int
    ):
        # Arrange
        headers = {"Authorization": f"Bearer {token_coordenador}"}
        payload = {
            "nome": "Juvenil A",
            "categoria": "SUB-16",
            "temporada_id": temporada_ativa_id,
            "capacidade_maxima": 18
        }
        
        # Act
        response = client.post("/api/v1/times", json=payload, headers=headers)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Juvenil A"
        assert data["id"] is not None
        assert "atletas" in data
    
    def test_criar_time_sem_autenticacao_deve_retornar_401(self, client):
        # Act
        response = client.post("/api/v1/times", json={})
        
        # Assert
        assert response.status_code == 401
    
    def test_criar_time_sem_permissao_deve_retornar_403(
        self, 
        client: TestClient,
        token_treinador: str  # Treinador não pode criar times
    ):
        # Arrange
        headers = {"Authorization": f"Bearer {token_treinador}"}
        payload = {"nome": "Time Teste", "categoria": "SUB-16"}
        
        # Act
        response = client.post("/api/v1/times", json=payload, headers=headers)
        
        # Assert
        assert response.status_code == 403
```

---

## 🎨 Padrões de Implementação

### 1. Arquitetura em Camadas

```
┌─────────────────────────────────────────────┐
│           API Layer (FastAPI)               │
│  • Routers                                  │
│  • Request/Response Models (Pydantic)       │
│  • Authentication/Authorization             │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Service Layer (Business Logic)      │
│  • Regras de negócio complexas              │
│  • Orquestração de operações                │
│  • Validações de domínio                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│       Repository Layer (Data Access)        │
│  • CRUD operations                          │
│  • Query builders                           │
│  • Transações                               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Model Layer (SQLAlchemy)            │
│  • ORM Models                               │
│  • Relationships                            │
│  • Database constraints                     │
└─────────────────────────────────────────────┘
```

### 2. Dependency Injection

```python
# core/dependencies.py
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    """Fornece sessão de banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extrai usuário autenticado do token."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(401, "Usuário inválido")
    
    return user

def require_role(*roles: str):
    """Dependency para verificar roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(403, "Permissão insuficiente")
        return current_user
    return role_checker

# Uso nos endpoints
@app.post("/times")
def criar_time(
    dados: CriarTimeRequest,
    current_user: User = Depends(require_role("COORDENADOR", "DIRIGENTE")),
    db: Session = Depends(get_db),
    servico: ServicoTime = Depends(get_servico_time)
):
    return servico.criar_time(dados, current_user.organizacao_id, db)
```

### 3. Repositórios Genéricos

```python
# core/repository.py
from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session

T = TypeVar('T')

class RepositorioBase(Generic[T]):
    """Repositório genérico com operações CRUD."""
    
    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db
    
    def buscar(self, id: int) -> Optional[T]:
        """Busca entidade por ID."""
        return self.db.query(self.model).get(id)
    
    def buscar_todos(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filtros: dict = None
    ) -> List[T]:
        """Busca todas as entidades com paginação."""
        query = self.db.query(self.model)
        
        if filtros:
            query = self._aplicar_filtros(query, filtros)
        
        return query.offset(skip).limit(limit).all()
    
    def criar(self, obj: T) -> T:
        """Cria nova entidade."""
        self.db.add(obj)
        self.db.flush()
        return obj
    
    def atualizar(self, obj: T) -> T:
        """Atualiza entidade existente."""
        self.db.merge(obj)
        self.db.flush()
        return obj
    
    def deletar(self, id: int) -> bool:
        """Deleta entidade por ID."""
        obj = self.buscar(id)
        if obj:
            self.db.delete(obj)
            self.db.flush()
            return True
        return False
    
    def _aplicar_filtros(self, query, filtros: dict):
        """Aplica filtros dinamicamente."""
        for campo, valor in filtros.items():
            if hasattr(self.model, campo):
                query = query.filter(getattr(self.model, campo) == valor)
        return query

# Uso específico
class RepositorioAtleta(RepositorioBase[Atleta]):
    """Repositório específico para Atletas."""
    
    def buscar_por_cpf(self, cpf: str) -> Optional[Atleta]:
        """Busca atleta por CPF."""
        return self.db.query(Atleta).filter(Atleta.cpf == cpf).first()
    
    def buscar_ativos_por_time(self, time_id: int) -> List[Atleta]:
        """Busca atletas ativos de um time."""
        return self.db.query(Atleta).join(Membership).filter(
            Membership.time_id == time_id,
            Membership.status == "ATIVO",
            Atleta.ativo == True
        ).all()
```

### 4. Value Objects

```python
# domain/value_objects.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CPF:
    """Value Object para CPF."""
    numero: str
    
    def __post_init__(self):
        if not self._validar(self.numero):
            raise ValueError(f"CPF inválido: {self.numero}")
    
    @staticmethod
    def _validar(cpf: str) -> bool:
        """Valida CPF usando algoritmo oficial."""
        # Remove caracteres não numéricos
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return False
        
        # Verifica se todos os dígitos são iguais
        if cpf_limpo == cpf_limpo[0] * 11:
            return False
        
        # Cálculo dos dígitos verificadores
        for i in range(9, 11):
            valor = sum((int(cpf_limpo[num]) * ((i + 1) - num) 
                        for num in range(0, i)))
            digito = ((valor * 10) % 11) % 10
            if digito != int(cpf_limpo[i]):
                return False
        
        return True
    
    def formatado(self) -> str:
        """Retorna CPF formatado: XXX.XXX.XXX-XX."""
        cpf = self.numero
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    
    def mascarado(self) -> str:
        """Retorna CPF mascarado: ***.XXX.XXX-**."""
        cpf = self.numero
        return f"***.{cpf[3:6]}.{cpf[6:9]}-**"

@dataclass(frozen=True)
class Email:
    """Value Object para Email."""
    endereco: str
    
    def __post_init__(self):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, self.endereco):
            raise ValueError(f"Email inválido: {self.endereco}")
    
    def dominio(self) -> str:
        """Retorna o domínio do email."""
        return self.endereco.split('@')[1]

# Uso nos modelos
class Atleta(Base):
    __tablename__ = "atletas"
    
    id = Column(Integer, primary_key=True)
    _cpf = Column("cpf", String(11), nullable=False, unique=True)
    _email = Column("email", String(255), nullable=False)
    
    @property
    def cpf(self) -> CPF:
        return CPF(self._cpf)
    
    @cpf.setter
    def cpf(self, valor: CPF):
        self._cpf = valor.numero
    
    @property
    def email(self) -> Email:
        return Email(self._email)
    
    @email.setter
    def email(self, valor: Email):
        self._email = valor.endereco
```

---

## ✅ Processo de Validação

### Checklist de Code Review

```markdown
## 📋 Checklist de Code Review - HB Track

### Qualidade de Código
- [ ] Complexidade ciclomática ≤ 6 por função
- [ ] Profundidade de aninhamento ≤ 3 níveis
- [ ] Funções com ≤ 50 linhas
- [ ] Métodos com ≤ 4 parâmetros
- [ ] Nomes descritivos e autoexplicativos
- [ ] Sem código duplicado (DRY)
- [ ] Comentários apenas onde necessário

### Arquitetura
- [ ] Baixo acoplamento entre módulos
- [ ] Alta coesão dentro de módulos
- [ ] Dependency Injection aplicado
- [ ] Responsabilidade única (SRP) respeitada
- [ ] Camadas bem definidas (API → Service → Repository → Model)

### Segurança
- [ ] Validação de entrada com Pydantic
- [ ] Autenticação/Autorização verificada
- [ ] Proteção contra SQL Injection
- [ ] Dados sensíveis não logados
- [ ] Rate limiting em endpoints críticos
- [ ] Tratamento adequado de erros (sem stack traces em produção)

### Testes
- [ ] Testes unitários para lógica de negócio
- [ ] Testes de integração para APIs
- [ ] Cobertura ≥ 75% (≥ 85% para código crítico)
- [ ] Testes de casos de borda
- [ ] Testes de validação negativa (erros esperados)
- [ ] Fixtures e mocks apropriados

### Documentação
- [ ] Docstrings em funções/classes públicas
- [ ] README atualizado (se necessário)
- [ ] ADR criado para decisões arquiteturais
- [ ] Comentários inline apenas onde crucial

### Performance
- [ ] Queries de banco otimizadas (sem N+1)
- [ ] Índices apropriados no banco
- [ ] Paginação implementada em listagens
- [ ] Sem operações bloqueantes no main thread

### Manutenibilidade
- [ ] Código facilmente extensível
- [ ] Sem "magic numbers" (usar constantes)
- [ ] Tratamento de exceções específico
- [ ] Logs estruturados e informativos
```

### Ferramentas de Validação Automatizada

```yaml
# .github/workflows/quality-check.yml
name: Quality Check

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Lint with Ruff
        run: ruff check .
      
      - name: Format check with Black
        run: black --check .
      
      - name: Type check with MyPy
        run: mypy app/
      
      - name: Security check with Bandit
        run: bandit -r app/ -ll
      
      - name: Complexity check with Radon
        run: |
          radon cc app/ -a -nb
          radon cc app/ -nc 6  # Falha se complexidade > 6
      
      - name: Run tests with coverage
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term
          coverage report --fail-under=75
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v2
```

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "C",   # flake8-comprehensions
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --strict-markers --cov=app"

[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
```

---

## 📚 Referências e Recursos

### Livros Recomendados
- **Clean Code** - Robert C. Martin
- **Refactoring** - Martin Fowler
- **Domain-Driven Design** - Eric Evans
- **Test Driven Development** - Kent Beck

### Padrões de Projeto
- Repository Pattern
- Unit of Work Pattern
- Strategy Pattern
- Factory Pattern
- Dependency Injection

### Ferramentas Essenciais
- **Linting:** Ruff, Pylint
- **Formatação:** Black, isort
- **Type Checking:** MyPy
- **Testing:** Pytest, Coverage.py
- **Security:** Bandit, Safety
- **Complexity:** Radon, McCabe

---

## 🔄 Processo de Melhoria Contínua

1. **Review Semanal:** Revisar métricas de qualidade do código
2. **Retrospectivas:** Discutir problemas encontrados e soluções
3. **Atualização de Padrões:** Evoluir este documento com aprendizados
4. **Treinamento:** Compartilhar conhecimento entre a equipe
5. **Automação:** Aumentar cobertura de validação automatizada

---

## ✍️ Assinaturas e Compromisso

Este documento representa o compromisso do projeto HB Track com excelência técnica, segurança e manutenibilidade.

**Versão:** 1.0  
**Data:** 2026-02-11  
**Última Revisão:** 2026-02-11  
**Próxima Revisão:** Trimestral

---
