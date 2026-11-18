"""Acceso a BigQuery con el blindaje de costos aplicado a TODAS las consultas.

Ningún otro módulo debe crear jobs de consulta por su cuenta: todo pasa por `consultar`,
que fija `maximum_bytes_billed` y permite hacer un dry run antes de ejecutar.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from string import Template
from typing import TYPE_CHECKING, Any

from observatorio.config import get_settings

if TYPE_CHECKING:
    from google.cloud import bigquery


class ConsultaDemasiadoCara(Exception):
    """La consulta escanearía más bytes que el tope configurado."""


@lru_cache
def cliente() -> bigquery.Client:
    from google.cloud import bigquery

    s = get_settings()
    return bigquery.Client(project=s.gcp_project or None, location=s.bq_location)


def _parametros(params: dict[str, Any] | None) -> list:
    from google.cloud import bigquery

    tipos = {bool: "BOOL", int: "INT64", float: "FLOAT64", str: "STRING", date: "DATE"}
    salida = []
    for nombre, valor in (params or {}).items():
        tipo = tipos.get(type(valor), "STRING")
        salida.append(bigquery.ScalarQueryParameter(nombre, tipo, valor))
    return salida


def estimar_bytes(sql: str, params: dict[str, Any] | None = None) -> int:
    """Dry run: BigQuery calcula los bytes que escanearía, sin ejecutar ni cobrar."""
    from google.cloud import bigquery

    config = bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False, query_parameters=_parametros(params)
    )
    job = cliente().query(sql, job_config=config)
    return int(job.total_bytes_processed or 0)


def consultar(
    sql: str,
    params: dict[str, Any] | None = None,
    *,
    verificar_antes: bool = False,
) -> list[dict[str, Any]]:
    """Ejecuta una consulta con tope de bytes. Devuelve las filas como diccionarios."""
    from google.cloud import bigquery

    tope = get_settings().max_bytes_billed
    if verificar_antes:
        estimado = estimar_bytes(sql, params)
        if estimado > tope:
            raise ConsultaDemasiadoCara(
                f"La consulta escanearía {estimado:,} bytes (tope {tope:,})."
            )

    config = bigquery.QueryJobConfig(
        maximum_bytes_billed=tope, query_parameters=_parametros(params)
    )
    filas = cliente().query(sql, job_config=config).result()
    return [dict(fila.items()) for fila in filas]


def renderizar_sql(plantilla: str) -> str:
    """Reemplaza $proyecto, $bronze, $silver y $gold en los archivos de sql/."""
    s = get_settings()
    return Template(plantilla).substitute(
        proyecto=s.gcp_project,
        bronze=s.dataset_bronze,
        silver=s.dataset_silver,
        gold=s.dataset_gold,
    )
