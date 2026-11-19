"""Extractores de cada fuente pública. Devuelven el archivo crudo y filas en formato largo."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

CABECERAS = {"User-Agent": "observatorio-afp (proyecto educativo)"}
INTENTOS = 4
ESPERA_INICIAL_S = 5


@dataclass(frozen=True)
class Extraccion:
    """Resultado de una extracción: el archivo tal cual llegó y sus filas en texto."""

    nombre_archivo: str
    contenido: bytes
    filas: list[dict[str, str]]


def descargar(url: str, timeout: float = 90, espera_inicial: float = ESPERA_INICIAL_S) -> bytes:
    """GET con reintentos y espera creciente (5 s, 10 s, 20 s) ante cortes o errores 5xx.

    Las fuentes son servicios públicos que a veces responden lento; un corte momentáneo no
    debe tumbar el job. Los errores 4xx no se reintentan: indican un problema de la petición.
    """
    for intento in range(1, INTENTOS + 1):
        try:
            respuesta = httpx.get(
                url, headers=CABECERAS, timeout=timeout, follow_redirects=True
            )
            if respuesta.status_code < 500:
                respuesta.raise_for_status()
                return respuesta.content
            error: Exception = httpx.HTTPStatusError(
                f"HTTP {respuesta.status_code}", request=respuesta.request, response=respuesta
            )
        except httpx.TransportError as falla:
            error = falla
        if intento == INTENTOS:
            raise error
        espera = espera_inicial * 2 ** (intento - 1)
        log.warning("Falló %s (%s). Reintento %d en %.0f s", url, error, intento, espera)
        time.sleep(espera)
    raise AssertionError("inalcanzable")
