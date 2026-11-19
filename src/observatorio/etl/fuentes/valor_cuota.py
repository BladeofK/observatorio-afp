"""Valor cuota y patrimonio de los fondos de pensiones (Superintendencia de Pensiones).

Formato real de la descarga (verificado en noviembre de 2026), texto separado por `;`:

    Valores Confirmados                         <- estado del bloque
    Fecha;CAPITAL;;CUPRUM;;...                  <- fila 1: AFP (cada una ocupa 2 columnas)
    ;Valor Cuota;Valor Patrimonio;...           <- fila 2: tipo de valor
    2026-01-01;84.438,32;7425745000772;...      <- datos: cuota con coma decimal y punto de
                                                   miles; patrimonio entero sin separadores
    (un bloque por año; las AFP cambian según el año)
    Valores Provisorios - Sujetos a Confirmacion
    ...                                         <- último bloque: días aún no confirmados

`fecconf` es la fecha de corte de la confirmación oficial: lo anterior sale como
"confirmado" y lo posterior como "provisorio". Se lee de la página del sitio, porque pasar
otra fecha cambia las etiquetas sin que los valores estén realmente confirmados.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from observatorio.config import get_settings
from observatorio.etl.fuentes import Extraccion, descargar

FONDOS = ("A", "B", "C", "D", "E")
_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FECCONF = re.compile(r"fecconf=(\d{8})")


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("latin-1")


def parsear(contenido: bytes, fondo: str) -> list[dict[str, str]]:
    """Convierte el archivo en filas largas (una por fecha y AFP), todo como texto.

    No convierte tipos: eso ocurre en silver. Bronze guarda los valores tal como vienen.
    """
    filas: list[dict[str, str]] = []
    estado = ""
    columnas: dict[int, tuple[str, str]] = {}  # índice -> (afp, "cuota" | "patrimonio")
    nombres_afp: list[str] = []

    for registro in csv.reader(io.StringIO(_decodificar(contenido)), delimiter=";"):
        celdas = [c.strip() for c in registro]
        if not celdas or not any(celdas):
            continue
        primera = celdas[0].lower()

        if primera.startswith("valores confirmados"):
            estado = "confirmado"
        elif primera.startswith("valores provisorios"):
            estado = "provisorio"
        elif primera == "fecha":
            nombres_afp = celdas
        elif primera == "" and nombres_afp:
            columnas = _mapear_columnas(nombres_afp, celdas)
        elif _FECHA.match(celdas[0]) and columnas:
            filas.extend(_filas_del_dia(celdas, columnas, fondo, estado))

    if not columnas:
        raise ValueError("No se encontró el encabezado de dos filas (Fecha; AFP / Valor Cuota)")
    return filas


def _mapear_columnas(nombres: list[str], tipos: list[str]) -> dict[int, tuple[str, str]]:
    """Cada AFP aparece en la fila 1 y ocupa su columna y la siguiente (celda vacía)."""
    columnas: dict[int, tuple[str, str]] = {}
    afp_actual = ""
    for indice in range(1, len(tipos)):
        if indice < len(nombres) and nombres[indice]:
            afp_actual = nombres[indice]
        tipo = tipos[indice].lower()
        if afp_actual and "cuota" in tipo:
            columnas[indice] = (afp_actual, "cuota")
        elif afp_actual and "patrimonio" in tipo:
            columnas[indice] = (afp_actual, "patrimonio")
    return columnas


def _filas_del_dia(
    celdas: list[str], columnas: dict[int, tuple[str, str]], fondo: str, estado: str
) -> list[dict[str, str]]:
    por_afp: dict[str, dict[str, str]] = {}
    for indice, (afp, tipo) in columnas.items():
        valor = celdas[indice] if indice < len(celdas) else ""
        por_afp.setdefault(afp, {})[tipo] = valor

    return [
        {
            "fondo": fondo,
            "afp": afp,
            "fecha": celdas[0],
            "valor_cuota": valores.get("cuota", ""),
            "patrimonio": valores.get("patrimonio", ""),
            "estado": estado,
        }
        for afp, valores in por_afp.items()
        if valores.get("cuota")  # Sin dato ese día (p. ej. la AFP aún no existía)
    ]


def obtener_fecconf() -> str:
    """Lee la fecha de corte de confirmación (AAAAMMDD) desde la página del sitio."""
    pagina = _decodificar(descargar(get_settings().url_pagina_valor_cuota))
    encontrado = _FECCONF.search(pagina)
    if not encontrado:
        raise ValueError("No se encontró 'fecconf' en la página de valores cuota")
    return encontrado.group(1)


def extraer(fondo: str, desde: date, hasta: date, fecconf: str | None = None) -> Extraccion:
    if fondo not in FONDOS:
        raise ValueError(f"Fondo inválido: {fondo}")
    fecconf = fecconf or obtener_fecconf()
    url = get_settings().url_valor_cuota.format(
        anio_ini=desde.year, anio_fin=hasta.year, fondo=fondo, fecconf=fecconf
    )
    contenido = descargar(url)
    return Extraccion(
        nombre_archivo=f"valor_cuota_{fondo}_{desde.year}_{hasta.year}_conf{fecconf}.csv",
        contenido=contenido,
        filas=parsear(contenido, fondo),
    )
