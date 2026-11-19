# Imagen única: por defecto levanta la API; el job ETL sobrescribe el comando
# (python -m observatorio.etl.main diario). Una sola imagen = menos espacio en
# Artifact Registry (capa gratuita de 0,5 GB).
#
# Orden de capas pensado para el caché: lo que casi nunca cambia va primero. Si solo cambia
# el código o la documentación, las dependencias (~70 MB) se reutilizan y la imagen nueva
# agrega apenas unos KB al registro.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SQL_DIR=/app/sql \
    PORT=8080

WORKDIR /app
RUN useradd --create-home app

# 1) Dependencias: solo dependen de pyproject.toml. Se instala un paquete vacío con un
#    README provisorio para que pip resuelva e instale las dependencias, y luego se quita.
COPY pyproject.toml ./
RUN mkdir -p src/observatorio \
    && touch src/observatorio/__init__.py README.md \
    && pip install --no-cache-dir . \
    && pip uninstall --yes observatorio-afp \
    && rm -rf src README.md build

# 2) Código: cambia en casi todos los commits, pero esta capa pesa muy poco.
COPY README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && rm -rf build

COPY sql ./sql

USER app

CMD ["sh", "-c", "uvicorn observatorio.api.main:app --host 0.0.0.0 --port ${PORT}"]
