# OpenFHE (PyPI) é compilado para Ubuntu 24.04 / Python 3.12:
# exige Python 3.12 e glibc >= 2.39 (Debian trixie)
FROM python:3.12-slim-trixie

WORKDIR /app

# libgomp1: OpenMP, usado pelo OpenFHE | curl: healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 8000

# Aplica as migrações pendentes antes de iniciar a API
CMD ["sh", "-c", "alembic upgrade head && fastapi run src/app.py --host 0.0.0.0 --port 8000"]
