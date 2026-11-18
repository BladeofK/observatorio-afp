"""Cada barrera del LLM tiene su test: si alguno falla, el endpoint /preguntar no es seguro."""

import pytest

from observatorio.llm.barreras import SQLRechazado, validar_sql

TABLAS = {"rentabilidad_mensual", "ranking_fondos", "indicadores_mensual"}


def validar(sql: str) -> str:
    return validar_sql(sql, "gold", TABLAS, proyecto_permitido="mi-proyecto")


def test_select_valido_recibe_limit():
    sql = validar("SELECT afp, rent_real_12m FROM `mi-proyecto.gold.ranking_fondos`")
    assert "LIMIT 100" in sql


def test_respeta_limit_razonable_y_recorta_excesivo():
    assert "LIMIT 10" in validar("SELECT afp FROM gold.ranking_fondos LIMIT 10")
    assert "LIMIT 1000" in validar("SELECT afp FROM gold.ranking_fondos LIMIT 999999")


def test_permite_cte_y_bloque_de_codigo_markdown():
    sql = validar(
        "```sql\nWITH t AS (SELECT afp FROM gold.rentabilidad_mensual) SELECT * FROM t\n```"
    )
    assert sql.startswith("WITH")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE gold.ranking_fondos",
        "DELETE FROM gold.ranking_fondos WHERE TRUE",
        "INSERT INTO gold.ranking_fondos (afp) VALUES ('X')",
        "UPDATE gold.ranking_fondos SET afp = 'X' WHERE TRUE",
        "CREATE TABLE gold.x AS SELECT 1 AS a",
        "SELECT 1; DROP TABLE gold.ranking_fondos",
    ],
)
def test_rechaza_escritura_y_multiples_sentencias(sql):
    with pytest.raises(SQLRechazado):
        validar(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM silver.valor_cuota",
        "SELECT * FROM bronze.valor_cuota_raw",
        "SELECT * FROM gold.tabla_que_no_existe",
        "SELECT * FROM `otro-proyecto.gold.ranking_fondos`",
        "SELECT * FROM gold.INFORMATION_SCHEMA.TABLES",
        "SELECT * FROM gold.ranking_fondos JOIN silver.indicadores USING (mes)",
        "SELECT * FROM gold.ranking_fondos WHERE afp IN (SELECT afp FROM silver.valor_cuota)",
    ],
)
def test_rechaza_tablas_fuera_de_la_lista_blanca(sql):
    with pytest.raises(SQLRechazado):
        validar(sql)


def test_rechaza_sql_invalido():
    with pytest.raises(SQLRechazado):
        validar("esto no es sql")
