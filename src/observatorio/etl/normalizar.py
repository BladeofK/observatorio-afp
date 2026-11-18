"""Conversión de texto a tipos, usada por las reglas de calidad.

Silver hace la conversión equivalente en SQL (ver sql/silver/). Mantener ambas alineadas.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

FORMATOS_FECHA = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")


def a_fecha(texto: str) -> date | None:
    texto = (texto or "").strip()[:10]
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def a_numero_chileno(texto: str) -> Decimal | None:
    """'61.234,56' -> Decimal('61234.56'). Punto de miles y coma decimal."""
    texto = (texto or "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(texto) if texto else None
    except InvalidOperation:
        return None


def a_numero(texto: str) -> Decimal | None:
    """'36789.36' -> Decimal('36789.36'). Formato con punto decimal (JSON)."""
    try:
        return Decimal((texto or "").strip()) if texto else None
    except InvalidOperation:
        return None


def nombre_afp(texto: str) -> str:
    """'AFP Plan Vital' / 'PLANVITAL' -> 'PLANVITAL'. Igual a la normalización de silver."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^A-Za-z]", "", sin_tildes).upper()
    return limpio.removeprefix("AFP")
