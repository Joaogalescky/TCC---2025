# Variáveis
PYTHON_VERSION=3.13
PYENV=3.13.5

.PHONY: all setup poetry python deps dev test lint

# Instalar tudo
all: setup poetry python deps dev

# Caso queira utilizar o venv no lugar do poetry
venv:
	python -m venv venv

# Para o venv
requirements:
	pip install -r requirements.txt

# Pipx
setup:
	pyenv install $(PYENV)
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
	poetry add --group dev pytest pytest-cov taskipy ruff pydantic[email]