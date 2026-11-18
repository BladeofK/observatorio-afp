"""Ejecuta los archivos SQL versionados en sql/ (DDL, silver y gold), en orden alfabético."""

from __future__ import annotations

import logging
from pathlib import Path

from observatorio.bq import consultar, renderizar_sql
from observatorio.config import get_settings

log = logging.getLogger(__name__)


def directorio_sql() -> Path:
    # En el repo: <raíz>/sql. En Docker se fija SQL_DIR=/app/sql.
    configurado = get_settings().sql_dir
    return Path(configurado) if configurado else Path(__file__).resolve().parents[3] / "sql"


def ejecutar_directorio(subdirectorio: str) -> None:
    carpeta = directorio_sql() / subdirectorio
    archivos = sorted(carpeta.glob("*.sql"))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos .sql en {carpeta}")
    for archivo in archivos:
        log.info("Ejecutando %s/%s", subdirectorio, archivo.name)
        consultar(renderizar_sql(archivo.read_text(encoding="utf-8")))
