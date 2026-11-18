"""Valor cuota y patrimonio de los fondos de pensiones (Superintendencia de Pensiones).

POR CONFIRMAR EN FASE 1: el formato exacto del archivo. Este parser asume el formato
"ancho" típico de la descarga: separador `;`, coma decimal, punto de miles, una fila por
fecha y dos columnas por AFP ("<AFP> Valor Cuota", "<AFP> Valor Patrimonio"), precedidas por
líneas de título. Si el archivo real difiere, ajustar `parsear` y `tests/fixtures/`.
"""

from __future__ import annotations

import csv
import io
from datetime import date

import httpx

from observatorio.config import get_settings
from observatorio.etl.fuentes import Extraccion

FONDOS = ("A", "B", "C", "D", "E")
SUFIJO_CUOTA = "valor cuota"
SUFIJO_PATRIMONIO = "valor patrimonio"


def _decodificar(contenido: bytes) -> str:
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ValueError("No se pudo decodificar el archivo de valor cuota")


def parsear(contenido: bytes, fondo: str) -> list[dict[str, str]]:
    """Convierte el archivo ancho en filas largas (una por fecha y AFP), todo como texto.

    No convierte tipos: eso ocurre en silver. Bronze guarda los valores tal como vienen.
    """
    lineas = _decodificar(contenido).splitlines()
    inicio = next(
        (i for i, linea in enumerate(lineas) if linea.strip().lower().startswith("fecha")),
        None,
    )
    if inicio is None:
        raise ValueError("No se encontró la fila de encabezado que empieza con 'Fecha'")

    lector = csv.reader(io.StringIO("\n".join(lineas[inicio:])), delimiter=";")
    encabezado = [col.strip() for col in next(lector)]

    # Mapa AFP -> (índice valor cuota, índice patrimonio)
    columnas: dict[str, dict[str, int]] = {}
    for indice, nombre in enumerate(encabezado[1:], start=1):
        minuscula = nombre.lower()
        for sufijo, clave in ((SUFIJO_CUOTA, "cuota"), (SUFIJO_PATRIMONIO, "patrimonio")):
            if minuscula.endswith(sufijo):
                afp = nombre[: -len(sufijo)].strip()
                columnas.setdefault(afp, {})[clave] = indice

    filas: list[dict[str, str]] = []
    for registro in lector:
        if not registro or not registro[0].strip():
            continue
        fecha = registro[0].strip()
        for afp, indices in columnas.items():
            cuota = _celda(registro, indices.get("cuota"))
            if not cuota:
                continue  # La AFP no tiene dato ese día (p. ej. aún no existía)
            filas.append(
                {
                    "fondo": fondo,
                    "afp": afp,
                    "fecha": fecha,
                    "valor_cuota": cuota,
                    "patrimonio": _celda(registro, indices.get("patrimonio")),
                }
            )
    return filas


def _celda(registro: list[str], indice: int | None) -> str:
    if indice is None or indice >= len(registro):
        return ""
    return registro[indice].strip()


def extraer(fondo: str, desde: date, hasta: date) -> Extraccion:
    if fondo not in FONDOS:
        raise ValueError(f"Fondo inválido: {fondo}")
    url = get_settings().url_valor_cuota.format(
        anio_ini=desde.year, anio_fin=hasta.year, fondo=fondo, fecha=hasta.isoformat()
    )
    respuesta = httpx.get(url, timeout=60, follow_redirects=True)
    respuesta.raise_for_status()
    contenido = respuesta.content
    return Extraccion(
        nombre_archivo=f"valor_cuota_{fondo}_{desde.year}_{hasta.year}.csv",
        contenido=contenido,
        filas=parsear(contenido, fondo),
    )
