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
- **Provas Zero-Knowledge**: Validação do voto no momento da cifragem (simulada; ver Limitações)

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
│   ├── crypto_service.py      # Serviço de criptografia homomórfica e chaves persistentes
│   ├── voting.py              # Voto, lotes, regra de decifragem e apuração
│   ├── admin.py               # Criação do administrador na inicialização
│   ├── app.py                 # Aplicação FastAPI principal
│   └── routers/               # Módulos de rotas da API
│       ├── auth.py            # Endpoints de autenticação
│       ├── users.py           # Gerenciamento de usuários
│       ├── candidates.py      # Consulta de candidatos
│       ├── elections.py       # Gerenciamento de eleições
│       ├── vote.py            # Sistema de votação
│       └── events.py          # Server-Sent Events
├── migrations/                # Migrações de banco de dados
├── keys/                      # Contexto e chaves do OpenFHE (gerado; fora do Git)
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
- **Voto 1-Hot**: Vetor com 1 na posição do candidato e 0 nas demais, cifrado num único ciphertext
- **Chaves Persistentes**: Contexto e chaves gerados uma vez e carregados ao iniciar
- **Provas Zero-Knowledge**: Verificação simulada no momento do voto (não gravada)

### 2. Gerenciamento de Eleições

#### Estrutura de Dados
```sql
-- Usuários (eleitores, candidatos e administrador)
usuarios (id, username, password, email, statusVotacao, is_candidate, is_admin, deleted_at, created_at, updated_at)

-- Eleições (status: draft, open, closed, tallied ou cancelled)
eleicoes (id, title, status, created_at, updated_at)

-- Associação Eleição-Candidato (fk_candidate referencia usuarios;
-- posicao = posição no vetor 1-hot, fixada ao abrir a eleição)
eleicao_candidato (id, fk_election, fk_candidate, posicao)

-- Total cifrado da eleição, criado ao abrir a votação
registro_eleicao (id, fk_election, encrypted_tally, total_candidates, total_votos,
                  lotes_fechados, hash_ultimo_lote, resultado_json)

-- Quem já votou (impede voto duplo sem ligar a pessoa ao voto) — WITHOUT ROWID
participacoes (fk_user, fk_election)

-- Votos do lote aberto, apagados quando o lote fecha — WITHOUT ROWID
votos (id UUID4, fk_election, encrypted_vote, receipt_hash)

-- Subtotal cifrado de cada lote fechado
subtotais_lote (id, fk_election, numero_lote, qtd_votos, encrypted_subtotal, hash_lote)

-- Comprovantes dos lotes fechados — WITHOUT ROWID
comprovantes (receipt_hash, fk_election, numero_lote)
```

Nenhuma tabela ligada a votos guarda horário, ordem de chegada ou o eleitor. Em SQLite uma tabela comum tem um `rowid` na ordem de inserção; por isso `votos`, `participacoes` e `comprovantes` são `WITHOUT ROWID`, com chave primária não sequencial. O banco usa `PRAGMA secure_delete`, que sobrescreve com zeros os votos apagados ao fechar um lote.

#### Funcionalidades
- **CRUD de Eleições**: Criação, leitura, atualização e exclusão ou cancelamento (somente administrador)
- **Associação de Candidatos**: Vinculação de candidatos às eleições (somente administrador)
- **Total Cifrado**: Soma homomórfica incremental, voto a voto, mais subtotais por lote
- **Abertura, Encerramento e Apuração**: O administrador abre a votação, encerra e depois apura os votos

#### Papéis de Usuário
- **Eleitor**: Todo usuário cadastrado; pode votar
- **Candidato**: Usuário marcado pelo administrador (`is_candidate`); também vota e pode ser vinculado a eleições
- **Administrador**: Criado na inicialização a partir das variáveis `ADMIN_*` (`is_admin`); gerencia eleições e candidatos

#### Ciclo de Vida da Eleição
| Status | Significado | Permitido |
|--------|-------------|-----------|
| `draft` | Em configuração | Vincular e remover candidatos; ainda não é possível votar |
| `open` | Aberta | Votar; lista de candidatos travada |
| `closed` | Encerrada | Nenhum voto novo; lista de candidatos travada; resultado sigiloso |
| `tallied` | Apurada | Resultado público; eleição mantida como histórico (não pode ser excluída) |
| `cancelled` | Cancelada | Exclusão lógica de eleição aberta ou encerrada; votos e candidatos mantidos, sem apuração |

#### Regras
- Toda eleição é criada em configuração (`draft`)
- Candidatos só podem ser vinculados ou removidos enquanto a eleição está em configuração
- Para abrir a votação, a eleição precisa ter pelo menos dois candidatos
- Candidato vinculado a uma eleição não pode ser desmarcado como candidato
- A apuração exige a eleição encerrada e ocorre uma única vez
- Eleição apurada não pode ser excluída nem cancelada
- Eleição sem votos pode ser excluída definitivamente, junto com vínculos e registro
- Eleição aberta ou encerrada com votos não pode ser excluída, apenas cancelada

#### Exclusão de Usuários
- O próprio usuário ou o administrador podem excluir uma conta; contas de administrador não podem ser excluídas
- Exclusão física: quem nunca votou nem foi candidato numa eleição aberta
- Exclusão lógica (`deleted_at`): quem já participou; a conta perde o acesso (login e tokens), mas votos e candidaturas ficam no histórico e o e-mail e o nome continuam reservados
- O administrador pode reativar uma conta excluída logicamente
- Vínculos com eleições em configuração são removidos na exclusão
- Candidato excluído logicamente continua na cédula das eleições abertas, marcado com `is_deleted`, e pode receber votos; não pode ser vinculado a novas eleições

### 3. Sistema de Votação

#### Processo de Votação
Tudo numa única transação serializada (`asyncio.Lock` + `BEGIN IMMEDIATE` no SQLite), para que dois votos simultâneos não leiam o mesmo total. Em qualquer erro, nada é gravado.
1. **Validação**: Usuário autenticado, eleição aberta e candidato da eleição
2. **Prevenção de Voto Duplo**: Consulta a `participacoes` (409 se já votou)
3. **Cifragem**: Vetor 1-hot com a posição do candidato, cifrado e serializado em bytes
4. **Prova ZK**: Verificada no momento do voto e não gravada
5. **Gravação**: `participacoes` e `votos` (bytes e comprovante), sem ligação entre os dois
6. **Total**: Soma homomórfica ao `encrypted_tally` e `total_votos + 1`
7. **Lote**: Se o lote aberto completou `LOTE_TAMANHO` votos, ele é fechado na mesma transação
8. **Resposta**: `{"message": ..., "receipt": "<sha256>"}`; o comprovante não é registrado em log

#### Lotes e Comprovantes
- **Comprovante**: SHA-256 do voto cifrado, entregue ao eleitor; não revela o candidato
- **Fechamento de lote**: Os votos do lote são somados do zero num subtotal cifrado, os comprovantes vão para `comprovantes` (sempre lidos ordenados pelo próprio hash) e os votos individuais são apagados
- **Cadeia de hashes**: `hash_lote = sha256(hash anterior | número | quantidade | comprovantes | sha256(subtotal))`, começando em `"0" * 64`
- **Fechamento final**: Ao encerrar (ou cancelar) a eleição, o lote aberto é fechado mesmo com poucos votos; nenhum voto individual fica no banco

#### Regra de Decifragem
Uma única função (`voting.decrypt_lots`) decifra conjuntos de lotes. Um conjunto parcial só é decifrado se **ele e o seu complemento** tiverem pelo menos `LOTE_MINIMO_DECIFRAR` votos; isso impede o ataque por diferença (o total menos um conjunto quase completo revelaria os votos restantes). O conjunto com todos os lotes, sem votos fora deles, é o resultado final. Votos individuais nunca são decifrados, e não há rota pública para decifrar lotes.

#### Apuração com Dupla Contagem
1. **Caminho 1**: Decifra o total acumulado voto a voto
2. **Caminho 2**: Soma os subtotais de todos os lotes e decifra
3. **Verificações**: Os dois resultados iguais; soma dos votos = `total_votos` = participações = soma das quantidades dos lotes; cadeia de hashes íntegra
4. **Resultado**: Gravado em `resultado_json` e publicado; `GET /vote/results/{id}` só lê esse resultado
5. **Falha**: Responde 409 com a verificação que falhou e a eleição continua encerrada

### 4. Autenticação e Autorização

#### Sistema JWT
- **Geração de Tokens**: Tokens com expiração configurável
- **Validação Automática**: Middleware de autenticação
- **Refresh Tokens**: Renovação de sessões

#### Segurança de Senhas
- **Hash Argon2**: Algoritmo resistente a ataques de força bruta
- **Salt Automático**: Proteção contra rainbow tables

## Configuração e Execução

### Pré-requisitos
- Python 3.12 (exigido pelo pacote OpenFHE do PyPI)
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

# Administrador criado ao iniciar a API, se ainda não existir
ADMIN_USERNAME='admin'
ADMIN_EMAIL='admin@admin.com'
ADMIN_PASSWORD='troque-esta-senha'

# Lotes de votos (LOTE_TAMANHO >= LOTE_MINIMO_DECIFRAR >= 1)
LOTE_TAMANHO=1000
LOTE_MINIMO_DECIFRAR=100

# Pasta das chaves do OpenFHE; sem a variável, usa fast_backend/keys
# KEYS_DIR='/caminho/para/keys'
```

Na primeira inicialização o backend gera o contexto e as chaves em `KEYS_DIR` (`cryptocontext.bin`, `public.key`, `secret.key` com permissão 600 e `evalmult.key`); nas seguintes, carrega esses arquivos. Banco e chaves andam juntos: com chaves novas, os votos já gravados não podem ser decifrados.

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

Rotas marcadas com **(admin)** exigem um usuário administrador.

### Usuários
- `POST /users`: Cadastro de usuário (sempre como eleitor)
- `GET /users`: Listagem de usuários
- `GET /users/me`: Usuário autenticado
- `GET /users/{id}`: Usuário específico
- `PUT /users/{id}`: Atualização completa
- `PATCH /users/{id}`: Atualização parcial
- `PATCH /users/{id}/candidate`: Marcar ou desmarcar como candidato **(admin)**
- `DELETE /users/{id}`: Exclusão da própria conta ou pelo administrador (física ou lógica)
- `POST /users/{id}/reactivate`: Reativar conta excluída logicamente **(admin)**

### Candidatos
- `GET /candidates`: Listagem de usuários marcados como candidatos
- `GET /candidates/{id}`: Candidato específico

### Eleições
- `POST /elections`: Criação de eleição **(admin)**
- `GET /elections`: Listagem de eleições
- `GET /elections/{id}`: Eleição específica
- `PUT /elections/{id}`: Atualização de eleição **(admin)**
- `DELETE /elections/{id}`: Exclusão de eleição sem votos e não apurada **(admin)**
- `POST /elections/{id}/cancel`: Cancelar eleição aberta ou encerrada (exclusão lógica) **(admin)**
- `POST /elections/{id}/candidates/{candidate_id}`: Associar candidato, em configuração **(admin)**
- `DELETE /elections/{id}/candidates/{candidate_id}`: Desassociar candidato, em configuração **(admin)**
- `GET /elections/{id}/candidates`: Candidatos da eleição
- `POST /elections/{id}/open`: Confirmar a configuração e abrir a votação, com ao menos 2 candidatos **(admin)**
- `POST /elections/{id}/close`: Encerrar a votação **(admin)**
- `POST /elections/{id}/tally`: Apurar os votos e publicar o resultado **(admin)**

### Votação
- `POST /vote/election/{id}`: Submissão de voto criptografado (eleição aberta); devolve o comprovante
- `GET /vote/results/{id}`: Resultado gravado na apuração (nada é decifrado nesta rota)
- `GET /vote/receipt/{election_id}/{receipt_hash}`: Situação do comprovante: `pending` (lote aberto), `registered` com o número do lote, ou 404

### Auditoria
- `GET /elections/{id}/audit`: Lotes (número, quantidade, hash) com os comprovantes ordenados e `chain_valid`; não expõe textos cifrados

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
def add(self, ciphertext_a, ciphertext_b):
    # Soma homomórfica: slot-a-slot dos vetores empacotados
    return self.cc.EvalAdd(ciphertext_a, ciphertext_b)
```

#### Persistência
```python
crypto_service.load_or_create_keys(settings.KEYS_DIR)   # no lifespan da aplicação
encrypted_vote = crypto_service.serialize(ciphertext)  # bytes gravados no banco
ciphertext = crypto_service.deserialize(encrypted_vote)
```

A API antiga, com cache em memória por UUID (`encrypt_vote`, `add_vote_to_tally`, `decrypt_tally`...), foi mantida na classe `LegacyCacheAPI` só para os scripts de medição em `manual_tests/`; as rotas não a usam.

## Segurança e Privacidade

### Propriedades Criptográficas
- **Privacidade Semântica**: Votos individuais permanecem ocultos
- **Homomorfismo Aditivo**: Contabilização sem descriptografia
- **Verificabilidade**: Comprovante por eleitor e cadeia de hashes entre os lotes
- **Dupla Contagem**: Total acumulado conferido com a soma dos subtotais dos lotes
- **Integridade**: Proteção contra manipulação de votos

### Medidas de Segurança
- **Autenticação Forte**: JWT com expiração
- **Validação de Entrada**: Sanitização via Pydantic
- **Controle de Origem**: CORS restrito às origens do frontend
- **Controle de Acesso**: Rotas de gerenciamento restritas ao administrador
- **Logs**: As rotas `/vote/*` ficam fora do access log do uvicorn, para não registrar IP e horário de cada voto nem o comprovante consultado (que fica no caminho da URL)

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

### Tempos Medidos (votos persistentes por lote)
Medidos com `pytest tests/test_stress_voting.py -s` (3 candidatos, lote de 1.000 votos, parâmetros BFV atuais), no fluxo completo de serialização e dupla contagem:

| Etapa | Tempo |
|---|---|
| Voto: cifrar, serializar e somar ao total | 6,4 ms |
| Fechamento de lote (soma do zero de 1.000 votos lidos em bytes) | 2,6 s por lote |
| Apuração com dupla contagem, 1 lote / 10 lotes | 9 ms / 33 ms |
| Requisição de voto pela API (com banco, lote de 5 nos testes) | 17,5 ms |
| 100.000 votos só cifrados e somados em memória | 274 s |

O voto que completa um lote espera o fechamento (cerca de 2,6 s com 1.000 votos), porque tudo acontece na mesma transação.

### Métricas de Performance
- **Latência de Voto**: < 100ms por operação
- **Throughput**: > 1000 votos/segundo
- **Uso de Memória**: Votos e totais gravados como bytes no banco; sem dependência de cache
- **Escalabilidade**: Processamento em lotes para grandes volumes

## Considerações de Implementação

### Otimizações
- **Lotes de Votos**: Votos individuais só existem até o lote fechar; depois fica um subtotal por lote
- **Operações Assíncronas**: Não-bloqueio para alta concorrência

### Limitações
- **Módulo de Texto Plano**: Limite de 65537 votos por candidato
- **Profundidade Multiplicativa**: Limitação em operações complexas
- **Tamanho de Ciphertext**: Overhead criptográfico significativo (cerca de 385 KiB por voto serializado)
- **Prova ZK simulada**: `generate_zk_proof` só gera o hash de um dicionário; não prova que o voto cifrado é 1-hot
- **Cifragem no servidor**: O backend vê o voto no momento de cifrar; cifrar no navegador (OpenFHE em WebAssembly) é trabalho futuro
- **Chave privada única**: Quem tem acesso a `secret.key` e ao banco durante a votação poderia decifrar um voto do lote aberto; a mitigação futura é a decifragem por limiar (*threshold*), com a chave dividida entre várias pessoas
- **Resultado unânime ou eleição muito pequena**: Revela votos pelo próprio resultado, como em qualquer eleição
- **Horário de participação**: Votar marca `statusVotacao` e atualiza `usuarios.updated_at`, que registra quando a pessoa votou (não em quem)

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