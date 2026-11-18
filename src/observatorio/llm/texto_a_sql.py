"""Pregunta en lenguaje natural → SQL seguro → filas → respuesta redactada."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from observatorio import bq
from observatorio.config import get_settings
from observatorio.llm.barreras import validar_sql

# Esquema que conoce el modelo. Solo gold: es lo único que puede consultar.
TABLAS_GOLD = {
    "rentabilidad_mensual": (
        "mes DATE (primer día del mes), afp STRING (CAPITAL, CUPRUM, HABITAT, MODELO, "
        "PLANVITAL, PROVIDA, UNO), fondo STRING (A, B, C, D, E), valor_cuota_cierre NUMERIC, "
        "rent_nominal_mes FLOAT64, rent_nominal_12m FLOAT64, rent_real_12m FLOAT64 "
        "(proporciones: 0.05 = 5 %)"
    ),
    "ranking_fondos": (
        "mes DATE, fondo STRING, posicion INT64 (1 = mejor), afp STRING, "
        "rent_real_12m FLOAT64, rent_nominal_12m FLOAT64"
    ),
    "indicadores_mensual": "mes DATE, indicador STRING ('uf' o 'dolar'), valor_cierre NUMERIC",
}

PROMPT_SQL = """Eres un analista que escribe SQL de BigQuery (GoogleSQL).
Responde SOLO con una consulta SELECT, sin explicaciones ni bloques de código.
Usa nombres completos `{proyecto}.{dataset}.<tabla>`. No uses SELECT *.
Si la pregunta no se puede responder con estas tablas, responde exactamente: NO_APLICA

Tablas disponibles:
{esquema}

Pregunta: {pregunta}
"""

PROMPT_RESPUESTA = """Responde en español, en 2 a 4 frases, la pregunta usando SOLO estos datos.
Expresa las rentabilidades como porcentajes. Si los datos no bastan, dilo.
No des recomendaciones de inversión.

Pregunta: {pregunta}
Datos (JSON): {datos}
"""


class PreguntaNoAplica(ValueError):
    """La pregunta no se puede responder con los datos disponibles."""


@dataclass
class Respuesta:
    sql: str
    filas: list[dict[str, Any]]
    respuesta: str


@lru_cache
def _cliente_gemini():
    from google import genai

    return genai.Client(api_key=get_settings().gemini_api_key)


def _generar(prompt: str) -> str:
    s = get_settings()
    resultado = _cliente_gemini().models.generate_content(model=s.gemini_model, contents=prompt)
    return (resultado.text or "").strip()


def responder(pregunta: str) -> Respuesta:
    s = get_settings()
    esquema = "\n".join(f"- {tabla}: {columnas}" for tabla, columnas in TABLAS_GOLD.items())
    sql_generado = _generar(
        PROMPT_SQL.format(
            proyecto=s.gcp_project, dataset=s.dataset_gold, esquema=esquema, pregunta=pregunta
        )
    )
    if sql_generado.strip().upper() == "NO_APLICA":
        raise PreguntaNoAplica("La pregunta no se puede responder con los datos del observatorio.")

    sql_seguro = validar_sql(
        sql_generado,
        dataset_permitido=s.dataset_gold,
        tablas_permitidas=set(TABLAS_GOLD),
        proyecto_permitido=s.gcp_project,
    )
    filas = bq.consultar(sql_seguro, verificar_antes=True)
    datos = json.dumps(filas[:50], default=str, ensure_ascii=False)
    texto = _generar(PROMPT_RESPUESTA.format(pregunta=pregunta, datos=datos))
    return Respuesta(sql=sql_seguro, filas=filas, respuesta=texto)
