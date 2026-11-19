"""Pregunta en lenguaje natural → SQL seguro → filas → respuesta redactada."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

from observatorio import bq
from observatorio.config import get_settings
from observatorio.llm.barreras import validar_sql

log = logging.getLogger(__name__)

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
    "indicadores_mensual": (
        "mes DATE (primer día del mes), indicador STRING ('uf' o 'dolar'), valor_cierre NUMERIC "
        "(valor del último día del mes, en pesos). Úsala para preguntas sobre la UF o el dólar: "
        "nivel en un mes, o variación entre dos meses (diferencia y porcentaje)"
    ),
}

PROMPT_SQL = """Eres un analista que escribe SQL de BigQuery (GoogleSQL).
Responde SOLO con una consulta SELECT, sin explicaciones ni bloques de código.
Usa nombres completos `{proyecto}.{dataset}.<tabla>`. No uses SELECT *.
Reglas:
- Incluye en el SELECT las columnas que respaldan la respuesta (cifras y su mes), no solo
  el nombre de la AFP o el indicador.
- Toda columna calculada lleva un alias descriptivo en español (p. ej. AS variacion_uf).
- "Últimos 12 meses" = columnas *_12m del mes más reciente con datos.
- Para comparar valores en dos fechas, devuelve ambos valores además del resultado.
Contexto: hoy es {hoy}. Las tablas tienen datos mensuales desde enero de 2020 hasta el mes
actual, así que las fechas hasta hoy NO son futuras: consúltalas normalmente.
Responde exactamente NO_APLICA solo si la pregunta no trata de AFP, fondos de pensiones, UF o
dólar, o si pide algo distinto de leer estas tablas.

Tablas disponibles:
{esquema}

Pregunta: {pregunta}
"""

PROMPT_RESPUESTA = """Responde en español, en 2 a 4 frases, la pregunta usando SOLO estos datos.
Las columnas rent_* son proporciones (0.05 = 5 %): exprésalas como porcentajes.
El SQL indica qué representa cada columna. Si los datos no bastan, dilo.
No des recomendaciones de inversión.

Pregunta: {pregunta}
SQL ejecutado: {sql}
Datos (JSON): {datos}
"""


class PreguntaNoAplica(ValueError):
    """La pregunta no se puede responder con los datos disponibles."""


@dataclass
class Respuesta:
    sql: str
    filas: list[dict[str, Any]]
    respuesta: str


class LLMNoDisponible(RuntimeError):
    """Gemini no está configurado o no respondió (p. ej. cuota gratuita agotada)."""


@lru_cache
def _cliente_gemini():
    from google import genai
    from google.genai import types

    s = get_settings()
    # Versión de la API fijada explícitamente: los modelos de AI Studio (incluidos los alias
    # como gemini-flash-latest) se publican en v1beta, y la versión por defecto de la
    # librería puede cambiar entre releases (en noviembre de 2026 usaba v1 → error 404).
    # Sin reintentos internos y con tiempo límite: los reintentos los controla _generar,
    # probando modelos de respaldo dentro del presupuesto de tiempo de la pregunta.
    return genai.Client(
        api_key=s.gemini_api_key,
        http_options=types.HttpOptions(
            api_version="v1beta",
            timeout=int(s.gemini_timeout_s * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _modelos() -> list[str]:
    s = get_settings()
    respaldo = [m.strip() for m in s.gemini_modelos_respaldo.split(",") if m.strip()]
    return list(dict.fromkeys([s.gemini_model, *respaldo]))  # sin repetidos, en orden


def _generar(prompt: str, limite: float, llamar=None) -> str:
    """Prueba el modelo principal y luego los de respaldo hasta que uno responda.

    `limite` es el instante (time.monotonic) en que se agota el presupuesto de la pregunta.
    Ningún error cobra: la API key pertenece a un proyecto sin facturación (un 429 solo
    significa que se agotó la capa gratuita de ese modelo).
    """
    s = get_settings()
    if not s.gemini_api_key:
        raise LLMNoDisponible("El asistente con IA aún no está configurado.")
    llamar = llamar or _llamar_gemini

    ultimo = "se agotó el tiempo de espera"
    for modelo in _modelos():
        if time.monotonic() + s.gemini_timeout_s > limite:
            log.warning("Presupuesto de tiempo agotado antes de probar %s", modelo)
            ultimo = "se agotó el tiempo de espera"
            break
        try:
            return llamar(modelo, prompt)
        except Exception as error:  # noqa: BLE001 - cualquier falla pasa al siguiente modelo
            codigo = getattr(error, "code", type(error).__name__)
            mensaje = getattr(error, "message", str(error))
            # El mensaje de Gemini se registra (no contiene la API key) para diagnosticar.
            log.warning("Gemini respondió %s con el modelo %s: %s", codigo, modelo, mensaje)
            ultimo = str(codigo)
    raise LLMNoDisponible(
        f"El asistente con IA no está disponible ahora (último error: {ultimo}). "
        "Intenta de nuevo en unos minutos."
    )


def _llamar_gemini(modelo: str, prompt: str) -> str:
    from google.genai import types

    # Temperatura 0: la misma pregunta genera el mismo SQL (respuestas reproducibles).
    resultado = _cliente_gemini().models.generate_content(
        model=modelo, contents=prompt, config=types.GenerateContentConfig(temperature=0)
    )
    return (resultado.text or "").strip()


def responder(pregunta: str) -> Respuesta:
    s = get_settings()
    limite = time.monotonic() + s.gemini_presupuesto_s
    esquema = "\n".join(f"- {tabla}: {columnas}" for tabla, columnas in TABLAS_GOLD.items())
    sql_generado = _generar(
        PROMPT_SQL.format(
            proyecto=s.gcp_project,
            dataset=s.dataset_gold,
            esquema=esquema,
            pregunta=pregunta,
            hoy=date.today().isoformat(),
        ),
        limite,
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
    texto = _generar(
        PROMPT_RESPUESTA.format(pregunta=pregunta, sql=sql_seguro, datos=datos), limite
    )
    return Respuesta(sql=sql_seguro, filas=filas, respuesta=texto)
