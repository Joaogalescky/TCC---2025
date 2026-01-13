# Trabalho de Conclusão de Curso - 3° TADS | 2025

Repositório para o Trabalho de Conclusão de Curso (TCC) do curso de Tecnologia em Análise e Desenvolvimento de Sistemas - 3° TADS | Instituto Federal do Paraná - IFPR.

**Aluno:** João Vitor Campõe Galescky  
**Orientador:** Prof. M.e Edmar André Bellorini  
**Co-orientador:** Prof. Dr. Darlon Vasata

---

## Início Rápido

**Para pesquisadores e estudantes:** Este projeto está totalmente dockerizado para facilitar a continuidade da pesquisa.

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd TCC---2025

# 2. Verifique o ambiente
./check-environment.sh

# 3. Configure e inicie
cp .env.example .env
make docker-up

# 4. Acesse http://localhost:3000
```

**Documentação:** [DOCKER.md](DOCKER.md)

---

## Tema

**Criptografia Homomórfica Aplicada em um Sistema de Eleição**

Este projeto propõe a implementação de um sistema de eleição eletrônico que utiliza criptografia homomórfica para garantir a privacidade e a segurança dos votos, mesmo durante o processamento.

---

## Objetivos
### Objetivo Geral
Este trabalho tem como objetivo avaliar a viabilidade do uso da Criptografia Homomórfica em um sistema de eleição.

### Objetivos Específicos
- Avaliar a viabilidade da aplicação da criptografia totalmente homomórfica (FHE) em sistemas de eleição;
- Desenvolver um protótipo funcional de uma aplicação de eleição;
- Utilizar o esquema de criptografia BFV (Brakerski/Fan-Vercauteren);
- Armazenar votos criptografados em banco de dados relacional;
- Garantir segurança, confidencialidade, integridade e anonimato durante o processo de eleição.

---

## Tecnologias Utilizadas

### Frameworks
- [Svelte](https://svelte.dev) – Front-End;
- [FastAPI](https://fastapi.tiangolo.com) – Back-End.

### Linguagens
- JavaScript;
- Typescript;
- Python;
- SQL.

### Bibliotecas e Dependências
- [OpenFHE](https://openfhe.org/) – Biblioteca de criptografia homomórfica baseada no esquema BFV.

### Banco de Dados
- [SQLite](https://sqlite.org/)

---

## Ferramentas de Desenvolvimento
- [Visual Studio Code](https://code.visualstudio.com) – Editor de código-fonte;
- [MySQL Workbench](https://www.mysql.com/products/workbench) – Modelagem;
- [Beekeper Studio](https://www.beekeeperstudio.io/pt-br/) - Administração do banco de dados SQL;
- [PlantUML](https://plantuml.com/) - Diagramação.

---

## Esquema Criptográfico

- **BFV (Brakerski-Fan-Vercauteren):** Esquema de criptografia homomórfica que permite operações de adição e multiplicação sobre dados criptografados.

---

## Como Executar o Projeto

### Opção 1: Usando Docker (Recomendado)

#### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

#### Passos para Execução

1. **Clone o repositório:**
```bash
git clone <url-do-repositorio>
cd TCC---2025
```

2. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

3. **Inicie os containers:**
```bash
make docker-build
make docker-up
```

Ou diretamente:
```bash
docker-compose up --build -d
```

4. **Acesse a aplicação:**
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Documentação da API:** http://localhost:8000/docs
- **MySQL:** localhost:3306

#### Comandos Úteis

```bash
# Ver logs dos containers
make docker-logs

# Parar os containers
make docker-down

# Reiniciar os containers
make docker-restart

# Ver status dos containers
make docker-ps

# Limpar containers e volumes
make docker-clean
```

### Opção 2: Instalação Local

#### Backend (FastAPI)

1. **Instale as dependências:**
```bash
cd fast_backend
pip install poetry
poetry install
```

2. **Configure o banco de dados e variáveis de ambiente**

3. **Execute o servidor:**
```bash
poetry run fastapi dev src/app.py
```

#### Frontend (Svelte)

1. **Instale as dependências:**
```bash
cd svelte_frontend
npm install
```

2. **Execute o servidor de desenvolvimento:**
```bash
npm run dev
```

---

## Instituição

[![IFPR Logo](https://user-images.githubusercontent.com/126702799/234438114-4db30796-20ad-4bec-b118-246ebbe9de63.png)](https://www.ifpr.edu.br)

**Instituto Federal do Paraná - IFPR - Campus [Cascavel](https://ifpr.edu.br/cascavel/)**  
Curso: Tecnologia em Análise e Desenvolvimento de Sistemas.

---

> Documento elaborado com [StackEdit](https://stackedit.io).
