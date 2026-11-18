"""Carga a la capa bronze: archivo crudo en GCS y filas en texto en BigQuery.

BigQuery se carga SIEMPRE con load jobs (gratuitos), nunca con streaming inserts (pagados).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from observatorio.bq import cliente
from observatorio.config import get_settings
from observatorio.etl.fuentes import Extraccion


def guardar_crudo(fuente: str, extraccion: Extraccion, fecha_ingesta: date) -> str:
    """Sube el archivo original a gs://<bucket>/bronze/<fuente>/fecha_ingesta=.../"""
    from google.cloud import storage

    s = get_settings()
    ruta = f"bronze/{fuente}/fecha_ingesta={fecha_ingesta.isoformat()}/{extraccion.nombre_archivo}"
    blob = storage.Client(project=s.gcp_project or None).bucket(s.bucket).blob(ruta)
    blob.upload_from_string(extraccion.contenido)
    return f"gs://{s.bucket}/{ruta}"


def cargar_bronze(
    tabla: str, filas: list[dict[str, str]], archivo_origen: str, fecha_ingesta: date
) -> int:
    """Agrega las filas a bronze.<tabla> con un load job (WRITE_APPEND)."""
    from google.cloud import bigquery

    if not filas:
        return 0
    s = get_settings()
    ahora = datetime.now(UTC).isoformat()
    registros = [
        {
            **fila,
            "fecha_ingesta": fecha_ingesta.isoformat(),
            "ingesta_ts": ahora,
            "archivo_origen": archivo_origen,
        }
        for fila in filas
    ]
    destino = f"{s.gcp_project}.{s.dataset_bronze}.{tabla}"
    config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    cliente().load_table_from_json(registros, destino, job_config=config).result()
    return len(registros)
