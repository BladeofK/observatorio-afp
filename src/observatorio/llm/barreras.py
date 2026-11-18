"""Barreras de seguridad para SQL generado por un LLM.

Nunca se ejecuta SQL del modelo sin pasar por `validar_sql`. Reglas:
1. Una sola sentencia.
2. Solo lectura: SELECT o WITH ... SELECT (también UNION/INTERSECT/EXCEPT de SELECTs).
3. Ningún nodo de escritura o DDL en ninguna parte del árbol.
4. Solo tablas de la lista blanca (dataset gold).
5. LIMIT obligatorio y acotado.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

LIMITE_POR_DEFECTO = 100
LIMITE_MAXIMO = 1000

_PROHIBIDOS = tuple(
    getattr(exp, nombre)
    for nombre in (
        "Insert", "Update", "Delete", "Merge", "Create", "Drop",
        "Alter", "AlterTable", "TruncateTable", "Command", "Grant",
    )
    if hasattr(exp, nombre)
)
_CONSULTAS = (exp.Select, exp.Union, exp.Intersect, exp.Except)


class SQLRechazado(ValueError):
    """El SQL no cumple las barreras de seguridad."""


def validar_sql(
    sql: str,
    dataset_permitido: str,
    tablas_permitidas: set[str],
    proyecto_permitido: str = "",
) -> str:
    """Valida el SQL y devuelve una versión segura (con LIMIT). Lanza SQLRechazado si no."""
    sql = (sql or "").strip().removeprefix("```sql").removeprefix("```").removesuffix("```")
    sql = sql.strip()
    try:
        sentencias = [s for s in sqlglot.parse(sql, read="bigquery") if s is not None]
    except sqlglot.errors.ParseError as error:
        raise SQLRechazado(f"SQL inválido: {error}") from error

    if len(sentencias) != 1:
        raise SQLRechazado("Se permite exactamente una sentencia SQL.")
    arbol = sentencias[0]

    if not isinstance(arbol, _CONSULTAS):
        raise SQLRechazado("Solo se permiten consultas de lectura (SELECT).")
    for nodo in arbol.walk():
        if isinstance(nodo, _PROHIBIDOS):
            raise SQLRechazado(f"Operación no permitida: {type(nodo).__name__}.")

    nombres_cte = {cte.alias_or_name.lower() for cte in arbol.find_all(exp.CTE)}
    permitidas = {t.lower() for t in tablas_permitidas}
    for tabla in arbol.find_all(exp.Table):
        nombre = tabla.name.lower()
        dataset = (tabla.db or "").lower()
        if not dataset and nombre in nombres_cte:
            continue  # Referencia a un CTE definido en la misma consulta
        proyecto = (tabla.catalog or "").lower()
        proyecto_ajeno = proyecto and proyecto != proyecto_permitido.lower()
        if proyecto_ajeno or dataset != dataset_permitido.lower() or nombre not in permitidas:
            raise SQLRechazado(f"Tabla no permitida: {tabla.sql(dialect='bigquery')}.")

    limite = arbol.args.get("limit")
    valor_limite = _valor_limite(limite)
    if valor_limite is None or valor_limite > LIMITE_MAXIMO:
        arbol = arbol.limit(LIMITE_POR_DEFECTO if valor_limite is None else LIMITE_MAXIMO)

    return arbol.sql(dialect="bigquery")


def _valor_limite(limite: exp.Expression | None) -> int | None:
    if limite is None:
        return None
    expresion = limite.args.get("expression")
    if isinstance(expresion, exp.Literal) and expresion.is_int:
        return int(expresion.this)
    return LIMITE_MAXIMO + 1  # LIMIT no literal: se reemplaza por el máximo
