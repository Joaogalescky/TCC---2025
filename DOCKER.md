# Guia Docker - Sistema de Eleição

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+

## Início Rápido

```bash
# 1. Clonar repositório
git clone <url-do-repositorio>
cd TCC---2025

# 2. Configurar variáveis (troque SECRET_KEY e ADMIN_PASSWORD no .env)
cp .env.example .env

# 3. Iniciar containers
docker compose up --build -d

# 4. Acessar aplicação
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Comandos

### Iniciar
```bash
docker compose up -d
```

### Parar
```bash
docker compose down
```

### Ver logs
```bash
docker compose logs -f
```

### Rebuild
```bash
docker compose up --build -d
```

### Limpar tudo
```bash
docker compose down -v
docker system prune -a
```

## Estrutura

```
TCC---2025/
├── fast_backend/
│   ├── Dockerfile          # Container Python 3.12 + FastAPI + OpenFHE
│   └── src/
├── svelte_frontend/
│   ├── Dockerfile          # Container Node + Svelte
│   └── src/
└── docker-compose.yml      # Orquestração dos containers
```

## Serviços

### Backend (porta 8000)
- FastAPI
- OpenFHE (criptografia homomórfica)
- SQLite

### Frontend (porta 3000)
- SvelteKit
- Node.js

## Variáveis de Ambiente

Edite `.env` conforme necessário:

```bash
# Backend
DATABASE_URL=sqlite+aiosqlite:///database.db
SECRET_KEY=troque-por-uma-chave-secreta
PLAINTEXT_MODULUS=65537
MULTIPLICATIVE_DEPTH=2

# Administrador (criado ao iniciar o backend, se ainda não existir)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@admin.com
ADMIN_PASSWORD=troque-esta-senha

# Lotes de votos e chaves do OpenFHE
LOTE_TAMANHO=1000
LOTE_MINIMO_DECIFRAR=100
KEYS_DIR=/app/keys

# Frontend
ORIGIN=http://localhost:3000
PUBLIC_API_URL=http://localhost:8000
```

## Troubleshooting

### Porta em uso
Edite `docker-compose.yml` e mude a porta:
```yaml
ports:
  - "8001:8000"  # Muda de 8000 para 8001
```

### Container não inicia
```bash
docker compose logs backend
docker compose logs frontend
```

### Rebuild sem cache
```bash
docker compose build --no-cache
docker compose up -d
```

### Erro `No module named 'openfhe.openfhe'`
O pacote `openfhe` do PyPI é compilado para Ubuntu 24.04 / Python 3.12, apesar de ser publicado como `py3-none-any`. Por isso a imagem do backend usa `python:3.12-slim-trixie` (Python 3.12 e glibc >= 2.39). Não altere a versão do Python sem verificar a compatibilidade do OpenFHE.

### Erro `Defina SECRET_KEY no arquivo .env`
O arquivo `.env` não existe ou não define `SECRET_KEY`. Execute `cp .env.example .env` e defina uma chave.

### Erro `Defina ADMIN_EMAIL no arquivo .env`
O `.env` não define o e-mail do administrador. Preencha `ADMIN_USERNAME`, `ADMIN_EMAIL` e `ADMIN_PASSWORD`. O e-mail precisa ser válido: domínios reservados, como `.local`, são recusados.

### Volume de chaves `eleicao_keys`
O contexto e as chaves do OpenFHE ficam no volume nomeado `eleicao_keys`, montado em `/app/keys`. Eles são gerados na primeira inicialização e reaproveitados nas seguintes, o que permite apurar uma eleição mesmo depois de reiniciar o backend. A chave privada (`secret.key`) nunca vai para o Git nem para a imagem.

**Banco e chaves andam juntos.** Com chaves novas, os votos já gravados não podem ser decifrados; com banco novo e chaves antigas, nada se perde, mas o ideal é recriar os dois juntos.

### Recomeçar com o banco de dados vazio
O `docker-compose.yml` monta o arquivo `fast_backend/database.db` no container. Se o arquivo for apagado, o Docker cria uma **pasta** com esse nome e o backend não sobe. Para recomeçar, substitua o arquivo por um vazio e recrie também o volume de chaves:

```bash
docker compose down
docker volume rm tcc---2025_eleicao_keys   # nome = <pasta do projeto>_eleicao_keys
rm fast_backend/database.db
touch fast_backend/database.db
docker compose up -d
```

Ao iniciar, o backend aplica as migrações no arquivo vazio, gera chaves novas e cria o administrador definido no `.env`. Todos os usuários, eleições e votos anteriores são perdidos. Para ver o nome exato do volume: `docker volume ls | grep eleicao_keys`.

**Atualização para votos persistentes (migração `e7a3c9f1b5d8`):** os votos antigos guardavam só um identificador de um cache em memória e não podem ser recuperados. Essa migração exige começar com o banco vazio.

## Desenvolvimento

Para desenvolvimento local sem Docker, consulte o README.md principal.

## Produção

Para produção, altere:
1. SECRET_KEY no `.env`
2. Configure HTTPS
3. Use banco de dados externo (MySQL/PostgreSQL)
