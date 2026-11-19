"""Indicadores económicos diarios desde mindicador.cl (UF y dólar observado).

Formato de la API: {"codigo": "uf", "serie": [{"fecha": "2024-01-01T03:00:00.000Z",
"valor": 36789.36}, ...]}. La hora UTC corresponde a la medianoche en Chile, por lo que los
primeros 10 caracteres de `fecha` son la fecha local.
"""

from __future__ import annotations

import json

from observatorio.config import get_settings
from observatorio.etl.fuentes import Extraccion, descargar

INDICADORES = ("uf", "dolar")


def parsear(contenido: bytes, indicador: str) -> list[dict[str, str]]:
    datos = json.loads(contenido)
    return [
        {"indicador": indicador, "fecha": str(punto["fecha"]), "valor": str(punto["valor"])}
        for punto in datos.get("serie", [])
    ]


def extraer(indicador: str, anio: int) -> Extraccion:
    if indicador not in INDICADORES:
        raise ValueError(f"Indicador no soportado: {indicador}")
    url = get_settings().url_mindicador.format(indicador=indicador, anio=anio)
    contenido = descargar(url)
    return Extraccion(
        nombre_archivo=f"{indicador}_{anio}.json",
        contenido=contenido,
        filas=parsear(contenido, indicador),
    )
