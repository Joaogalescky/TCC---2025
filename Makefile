# Variáveis
PYTHON_VERSION=3.13

.PHONY: all setup poetry python deps dev test lint

# Instalar tudo
all: setup poetry python deps dev

# Pipx
setup:
	python3 -m pip install --user pipx
	pipx ensurepath

# Poetry
poetry:
	pipx install poetry

# Configura a versão do Python no poetry
python:
	poetry env use $(PYTHON_VERSION)

# Dependências principais
deps:
	poetry install

# Dependências de desenvolvimento
dev:
	poetry add --group dev pytest pytest-cov taskipy ruff