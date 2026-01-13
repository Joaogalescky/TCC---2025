# Backend - Sistema de Eleição com Criptografia Homomórfica

## Descrição

Este diretório implementa o núcleo do sistema de eleição eletrônico baseado em criptografia homomórfica totalmente funcional (FHE). Utilizando o esquema criptográfico BFV (Brakerski-Fan-Vercauteren) através da biblioteca OpenFHE, o sistema garante privacidade, integridade e verificabilidade dos votos durante todo o ciclo eleitoral, desde a submissão até a contabilização final.

## Arquitetura e Tecnologias

### Framework Principal
- **FastAPI**: Framework web moderno e de alta performance para Python
- **SQLAlchemy**: ORM assíncrono para manipulação de banco de dados
- **Alembic**: Sistema de migração de banco de dados
- **Pydantic**: Validação de dados e serialização

### Criptografia Homomórfica
- **OpenFHE**: Biblioteca de criptografia homomórfica
- **Esquema BFV**: Implementação do algoritmo Brakerski-Fan-Vercauteren
- **Provas Zero-Knowledge**: Validação de integridade dos votos

### Segurança e Autenticação
- **JWT (JSON Web Tokens)**: Autenticação stateless
- **Argon2**: Algoritmo de hash para senhas
- **PWDLib**: Biblioteca para gerenciamento seguro de senhas

### Banco de Dados
- **SQLite**: Banco de dados relacional (desenvolvimento)
- **Suporte Assíncrono**: Operações não-bloqueantes via aiosqlite

## Estrutura do Projeto

```
fast_backend/
├── src/
│   ├── models.py              # Modelos de dados SQLAlchemy
│   ├── schemas.py             # Esquemas Pydantic para validação
│   ├── database.py            # Configuração de conexão com banco
│   ├── security.py            # Autenticação e autorização
│   ├── settings.py            # Configurações da aplicação
│   ├── crypto_service.py      # Serviço de criptografia homomórfica
│   ├── app.py                 # Aplicação FastAPI principal
│   └── routers/               # Módulos de rotas da API
│       ├── auth.py            # Endpoints de autenticação
│       ├── users.py           # Gerenciamento de usuários
│       ├── candidates.py      # Gerenciamento de candidatos
│       ├── elections.py       # Gerenciamento de eleições
│       ├── vote.py            # Sistema de votação
│       └── events.py          # Server-Sent Events
├── migrations/                # Migrações de banco de dados
├── tests/                     # Testes automatizados
├── alembic.ini               # Configuração do Alembic
├── pyproject.toml            # Configurações do projeto Python
└── env.c                     # Variáveis de ambiente
```

## Funcionalidades Implementadas

### 1. Sistema Criptográfico Homomórfico

#### Configuração BFV
- **Módulo de Texto Plano**: 65537 (primo seguro)
- **Profundidade Multiplicativa**: 2 níveis
- **Empacotamento de Vetores**: Suporte a operações SIMD

#### Operações Criptográficas
- **Criptografia de Votos**: Transformação de votos em ciphertexts
- **Soma Homomórfica**: Agregação de votos sem descriptografia
- **Validação 1-Hot**: Garantia de voto único por eleição
- **Provas Zero-Knowledge**: Verificação de integridade sem revelação

### 2. Gerenciamento de Eleições

#### Estrutura de Dados
```sql
-- Eleições
eleicoes (id, title, created_at, updated_at)

-- Candidatos
candidatos (id, username, created_at, updated_at)

-- Associação Eleição-Candidato
eleicao_candidato (id, fk_election, fk_candidate)

-- Registro Criptografado da Eleição
registro_eleicao (id, fk_election, encrypted_tally, total_candidates, updated_at)
```

#### Funcionalidades
- **CRUD de Eleições**: Criação, leitura, atualização e exclusão
- **Associação de Candidatos**: Vinculação dinâmica de candidatos às eleições
- **Tally Criptografado**: Manutenção de contagem homomórfica

### 3. Sistema de Votação

#### Processo de Votação
1. **Validação de Elegibilidade**: Verificação de usuário autenticado
2. **Prevenção de Voto Duplo**: Controle de unicidade por eleição
3. **Criptografia Homomórfica**: Transformação do voto em ciphertext
4. **Geração de Prova ZK**: Criação de prova de validade
5. **Agregação Homomórfica**: Soma ao tally da eleição

#### Estrutura de Voto
```sql
votos (
    id,
    fk_user,
    fk_election_candidate,
    encrypted_vote,      -- Ciphertext do voto
    zk_proof,           -- Prova zero-knowledge
    created_at
)
```

### 4. Autenticação e Autorização

#### Sistema JWT
- **Geração de Tokens**: Tokens com expiração configurável
- **Validação Automática**: Middleware de autenticação
- **Refresh Tokens**: Renovação de sessões

#### Segurança de Senhas
- **Hash Argon2**: Algoritmo resistente a ataques de força bruta
- **Salt Automático**: Proteção contra rainbow tables
- **Validação de Força**: Critérios mínimos de segurança

## Configuração e Execução

### Pré-requisitos
- Python 3.13+
- Poetry (gerenciador de dependências)
- OpenFHE (biblioteca criptográfica)

### Instalação de Dependências
```bash
poetry install
```

### Configuração de Ambiente
Criar arquivo `.env` baseado em `env.c`:
```bash
DATABASE_URL='sqlite+aiosqlite:///database.db'
SECRET_KEY='MySecretKey'
ALGORITHM='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES=30
PLAINTEXT_MODULUS=65537
MULTIPLICATIVE_DEPTH=2
```

### Execução de Migrações
```bash
poetry run alembic upgrade head
```

### Execução em Modo de Desenvolvimento
```bash
poetry run task run
```
A API estará disponível em `http://localhost:8000`

### Execução de Testes
```bash
# Testes com cobertura
poetry run task test

# Apenas testes
poetry run pytest

# Testes de estresse
poetry run pytest tests/test_stress_voting.py -v
```

## API Endpoints

### Autenticação
- `POST /auth/token`: Obtenção de token JWT
- `POST /auth/refresh_token`: Renovação de token

### Usuários
- `POST /users`: Cadastro de usuário
- `GET /users`: Listagem de usuários
- `GET /users/{id}`: Usuário específico
- `PUT /users/{id}`: Atualização completa
- `PATCH /users/{id}`: Atualização parcial
- `DELETE /users/{id}`: Exclusão de usuário

### Candidatos
- `POST /candidates`: Cadastro de candidato
- `GET /candidates`: Listagem de candidatos
- `GET /candidates/{id}`: Candidato específico
- `PUT /candidates/{id}`: Atualização de candidato
- `DELETE /candidates/{id}`: Exclusão de candidato

### Eleições
- `POST /elections`: Criação de eleição
- `GET /elections`: Listagem de eleições
- `GET /elections/{id}`: Eleição específica
- `PUT /elections/{id}`: Atualização de eleição
- `DELETE /elections/{id}`: Exclusão de eleição
- `POST /elections/{id}/candidates/{candidate_id}`: Associar candidato
- `GET /elections/{id}/candidates`: Candidatos da eleição

### Votação
- `POST /vote/election/{id}`: Submissão de voto criptografado
- `GET /vote/results/{id}`: Resultados descriptografados

### Eventos
- `GET /events/elections`: Server-Sent Events para atualizações

## Implementação Criptográfica

### Classe HomomorphicElectionService

#### Configuração do Contexto
```python
def setup_crypto(self, plaintext_modulus=65537, multiplicative_depth=2):
    parameters = CCParamsBFVRNS()
    parameters.SetPlaintextModulus(plaintext_modulus)
    parameters.SetMultiplicativeDepth(multiplicative_depth)
    
    self.cc = GenCryptoContext(parameters)
    self.cc.Enable(PKESchemeFeature.PKE)
    self.cc.Enable(PKESchemeFeature.KEYSWITCH)
    self.cc.Enable(PKESchemeFeature.LEVELEDSHE)
```

#### Validação 1-Hot
```python
def validate_1hot_vector(self, vote_vector: List[int]) -> bool:
    if not all(x in {0, 1} for x in vote_vector):
        return False
    return sum(vote_vector) == 1 and len(vote_vector) > 0
```

#### Soma Homomórfica
```python
def add_vote_to_tally(self, encrypted_tally: str, encrypted_vote: str) -> str:
    ct_tally = self.ciphertext_cache[encrypted_tally]
    ct_vote = self.ciphertext_cache[encrypted_vote]
    ct_result = self.cc.EvalAdd(ct_tally, ct_vote)
    return self.manage_cache(self.generate_id(), ct_result)
```

## Segurança e Privacidade

### Propriedades Criptográficas
- **Privacidade Semântica**: Votos individuais permanecem ocultos
- **Homomorfismo Aditivo**: Contabilização sem descriptografia
- **Verificabilidade**: Provas zero-knowledge de validade
- **Integridade**: Proteção contra manipulação de votos

### Medidas de Segurança
- **Autenticação Forte**: JWT com expiração
- **Validação de Entrada**: Sanitização via Pydantic
- **Prevenção de Ataques**: Rate limiting e validação de origem
- **Auditoria**: Logs de todas as operações críticas

## Testes e Validação

### Testes Unitários
- **Cobertura Completa**: Todos os módulos testados
- **Mocks de Banco**: Testes isolados com SQLite em memória
- **Validação Criptográfica**: Testes de integridade das operações

### Testes de Estresse
- **100 Votos**: Processamento básico
- **1.000 Votos**: Teste de performance média
- **10.000 Votos**: Teste de alta carga
- **100.000 Votos**: Teste de escalabilidade extrema

### Métricas de Performance
- **Latência de Voto**: < 100ms por operação
- **Throughput**: > 1000 votos/segundo
- **Uso de Memória**: Cache FIFO com limite configurável
- **Escalabilidade**: Processamento em lotes para grandes volumes

## Considerações de Implementação

### Otimizações
- **Cache de Ciphertexts**: Gerenciamento FIFO para eficiência de memória
- **Processamento em Lotes**: Agregação eficiente de múltiplos votos
- **Operações Assíncronas**: Não-bloqueio para alta concorrência

### Limitações
- **Módulo de Texto Plano**: Limite de 65537 votos por candidato
- **Profundidade Multiplicativa**: Limitação em operações complexas
- **Tamanho de Ciphertext**: Overhead criptográfico significativo

## Fundamentos Teóricos

### Criptografia Homomórfica
A implementação baseia-se nos princípios matemáticos da criptografia homomórfica, permitindo computações sobre dados criptografados sem necessidade de descriptografia. O esquema BFV utilizado oferece:

- **Homomorfismo Aditivo**: Soma de ciphertexts resulta na soma dos plaintexts correspondentes
- **Segurança Semântica**: Impossibilidade de distinguir entre criptografias de mensagens diferentes
- **Resistência Quântica**: Baseado no problema Learning With Errors (LWE)

### Arquitetura de Segurança
O sistema implementa múltiplas camadas de segurança:

1. **Camada Criptográfica**: Proteção dos votos via FHE
2. **Camada de Autenticação**: Controle de acesso via JWT e Argon2
3. **Camada de Integridade**: Provas zero-knowledge para validação
4. **Camada de Auditoria**: Logs criptográficos para rastreabilidade