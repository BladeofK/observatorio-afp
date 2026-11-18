"""Extractores de cada fuente pública. Devuelven el archivo crudo y filas en formato largo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Extraccion:
    """Resultado de una extracción: el archivo tal cual llegó y sus filas en texto."""

    nombre_archivo: str
    contenido: bytes
    filas: list[dict[str, str]]
