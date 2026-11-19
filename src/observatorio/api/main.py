"""API REST del observatorio (FastAPI en Cloud Run).

Todas las consultas son parametrizadas y pasan por `bq.consultar`, que aplica el tope de
bytes facturados.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from observatorio import bq
from observatorio.api.limites import Limitador, LimiteExcedido
from observatorio.config import get_settings
from observatorio.llm.barreras import SQLRechazado

app = FastAPI(
    title="Observatorio de Fondos de Pensiones",
    description="Rentabilidad de los fondos de pensiones chilenos a partir de datos públicos.",
    version="0.1.0",
)

Fondo = Literal["A", "B", "C", "D", "E"]
_settings = get_settings()
limitador = Limitador(_settings.llm_max_por_minuto_ip, _settings.llm_max_diario)


def _tabla(nombre: str) -> str:
    s = get_settings()
    return f"`{s.gcp_project}.{s.dataset_gold}.{nombre}`"


@app.get("/salud")
def salud() -> dict[str, str]:
    return {"estado": "ok"}


@app.get("/fondos/rentabilidad")
def rentabilidad(
    fondo: Fondo,
    afp: Annotated[str | None, Query(description="Ej.: MODELO. Sin valor: todas")] = None,
    desde: date = date(2020, 1, 1),
) -> list[dict]:
    sql = f"""
        SELECT mes, afp, fondo, valor_cuota_cierre,
               rent_nominal_mes, rent_nominal_12m, rent_real_12m
        FROM {_tabla("rentabilidad_mensual")}
        WHERE fondo = @fondo
          AND mes >= @desde
          AND (@afp IS NULL OR afp = UPPER(@afp))
        ORDER BY afp, mes
    """
    return bq.consultar(sql, {"fondo": fondo, "desde": desde, "afp": afp})


@app.get("/fondos/ranking")
def ranking(fondo: Fondo) -> list[dict]:
    sql = f"""
        SELECT mes, posicion, afp, rent_real_12m, rent_nominal_12m
        FROM {_tabla("ranking_fondos")}
        WHERE fondo = @fondo
        ORDER BY posicion
    """
    return bq.consultar(sql, {"fondo": fondo})


@app.get("/indicadores/{codigo}")
def indicador(codigo: Literal["uf", "dolar"], desde: date = date(2020, 1, 1)) -> list[dict]:
    sql = f"""
        SELECT mes, valor_cierre
        FROM {_tabla("indicadores_mensual")}
        WHERE indicador = @codigo AND mes >= @desde
        ORDER BY mes
    """
    return bq.consultar(sql, {"codigo": codigo, "desde": desde})


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=5, max_length=300)


class RespuestaLLM(BaseModel):
    respuesta: str
    sql: str
    filas: list[dict]


@app.post("/preguntar", response_model=RespuestaLLM)
def preguntar(cuerpo: Pregunta, request: Request) -> RespuestaLLM:
    from observatorio.llm.texto_a_sql import LLMNoDisponible, PreguntaNoAplica, responder

    if not get_settings().gemini_api_key:
        raise HTTPException(status_code=503, detail="El asistente con IA aún no está configurado.")

    # Cloud Run entrega la IP original en X-Forwarded-For.
    reenviada = request.headers.get("x-forwarded-for", "")
    ip = reenviada.split(",")[0].strip() or (request.client.host if request.client else "?")
    try:
        limitador.registrar(ip)
    except LimiteExcedido as error:
        raise HTTPException(status_code=429, detail=str(error)) from error

    try:
        resultado = responder(cuerpo.pregunta)
    except PreguntaNoAplica as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SQLRechazado as error:
        raise HTTPException(status_code=422, detail=f"Consulta rechazada: {error}") from error
    except bq.ConsultaDemasiadoCara as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LLMNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return RespuestaLLM(respuesta=resultado.respuesta, sql=resultado.sql, filas=resultado.filas)
