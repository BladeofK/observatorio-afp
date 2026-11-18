# Imagen única: por defecto levanta la API; el job ETL sobrescribe el comando
# (python -m observatorio.etl.main diario). Una sola imagen = menos espacio en
# Artifact Registry (capa gratuita de 0,5 GB).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SQL_DIR=/app/sql \
    PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY sql ./sql

RUN useradd --create-home app
USER app

CMD ["sh", "-c", "uvicorn observatorio.api.main:app --host 0.0.0.0 --port ${PORT}"]
