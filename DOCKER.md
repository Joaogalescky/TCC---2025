# Guia Docker - Sistema de Eleição

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+

## Início Rápido

```bash
# 1. Clonar repositório
git clone <url-do-repositorio>
cd TCC---2025

# 2. Configurar variáveis
cp .env.example .env

# 3. Instalar adapter-node no frontend
cd svelte_frontend
npm install @sveltejs/adapter-node
cd ..

# 4. Iniciar containers
docker-compose up --build -d

# 5. Acessar aplicação
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Comandos

### Iniciar
```bash
docker-compose up -d
```

### Parar
```bash
docker-compose down
```

### Ver logs
```bash
docker-compose logs -f
```

### Rebuild
```bash
docker-compose up --build -d
```

### Limpar tudo
```bash
docker-compose down -v
docker system prune -a
```

## Estrutura

```
TCC---2025/
├── fast_backend/
│   ├── Dockerfile          # Container Python + FastAPI + OpenFHE
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
SECRET_KEY=sua-chave-secreta
PLAINTEXT_MODULUS=65537
MULTIPLICATIVE_DEPTH=2

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
docker-compose logs backend
docker-compose logs frontend
```

### Rebuild sem cache
```bash
docker-compose build --no-cache
docker-compose up -d
```

### OpenFHE demora no primeiro build
O primeiro build do backend pode demorar 5-10 minutos devido à compilação do OpenFHE. Isso é normal.

## Desenvolvimento

Para desenvolvimento local sem Docker, consulte o README.md principal.

## Produção

Para produção, altere:
1. SECRET_KEY no `.env`
2. Configure HTTPS
3. Use banco de dados externo (MySQL/PostgreSQL)
