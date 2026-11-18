"""Punto de entrada del job ETL (Cloud Run Job o local).

Uso:
    python -m observatorio.etl.main setup                 # crea tablas bronze y silver
    python -m observatorio.etl.main ingestar              # extrae y carga bronze (últimos días)
    python -m observatorio.etl.main ingestar --desde 2022-01-01   # backfill
    python -m observatorio.etl.main transformar           # bronze → silver → gold
    python -m observatorio.etl.main diario                # ingestar + transformar
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta

from observatorio.etl import calidad, carga, transformar
from observatorio.etl.fuentes import indicadores, valor_cuota
from observatorio.etl.normalizar import a_fecha

# El job diario recarga los últimos días por si la fuente corrigió datos recientes.
DIAS_RECARGA_DIARIA = 10

log = logging.getLogger("observatorio.etl")


class FormatoJson(logging.Formatter):
    """Logs en JSON: Cloud Logging los interpreta y permite filtrar por severidad."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {"severity": record.levelname, "message": record.getMessage(), "logger": record.name},
            ensure_ascii=False,
        )


def _configurar_logs() -> None:
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoJson())
    logging.basicConfig(level=logging.INFO, handlers=[manejador], force=True)


def _revisar(nombre: str, reporte: calidad.Reporte) -> None:
    for advertencia in reporte.advertencias:
        log.warning("[%s] %s", nombre, advertencia)
    if not reporte.ok:
        for error in reporte.errores[:20]:
            log.error("[%s] %s", nombre, error)
        raise SystemExit(f"Calidad de datos fallida en {nombre}: {len(reporte.errores)} errores")


def _en_rango(filas: list[dict[str, str]], desde: date, hasta: date) -> list[dict[str, str]]:
    """Las fuentes entregan años completos; solo se cargan las fechas pedidas.

    Así el job diario carga pocos días y bronze no crece con copias repetidas del año.
    """
    salida = []
    for fila in filas:
        fecha = a_fecha(fila.get("fecha", ""))
        if fecha is None or desde <= fecha <= hasta:
            salida.append(fila)  # Las filas ilegibles pasan para que calidad las reporte
    return salida


def ingestar(desde: date, hasta: date) -> None:
    hoy = date.today()

    for fondo in valor_cuota.FONDOS:
        extraccion = valor_cuota.extraer(fondo, desde, hasta)
        filas = _en_rango(extraccion.filas, desde, hasta)
        _revisar(f"valor_cuota {fondo}", calidad.validar_valor_cuota(filas))
        ruta = carga.guardar_crudo("valor_cuota", extraccion, hoy)
        n = carga.cargar_bronze("valor_cuota_raw", filas, ruta, hoy)
        log.info("valor_cuota fondo %s: %d filas a bronze", fondo, n)

    for indicador in indicadores.INDICADORES:
        for anio in range(desde.year, hasta.year + 1):
            extraccion = indicadores.extraer(indicador, anio)
            filas = _en_rango(extraccion.filas, desde, hasta)
            _revisar(f"{indicador} {anio}", calidad.validar_indicadores(filas))
            ruta = carga.guardar_crudo("indicadores", extraccion, hoy)
            n = carga.cargar_bronze("indicadores_raw", filas, ruta, hoy)
            log.info("%s %d: %d filas a bronze", indicador, anio, n)


def main(argv: list[str] | None = None) -> None:
    _configurar_logs()
    parser = argparse.ArgumentParser(description="ETL Observatorio AFP")
    parser.add_argument("comando", choices=["setup", "ingestar", "transformar", "diario"])
    parser.add_argument("--desde", type=date.fromisoformat, default=None)
    parser.add_argument("--hasta", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)

    hasta = args.hasta or date.today()
    desde = args.desde or hasta - timedelta(days=DIAS_RECARGA_DIARIA)

    if args.comando == "setup":
        transformar.ejecutar_directorio("ddl")
    if args.comando in ("ingestar", "diario"):
        ingestar(desde, hasta)
    if args.comando in ("transformar", "diario"):
        transformar.ejecutar_directorio("silver")
        transformar.ejecutar_directorio("gold")
    log.info("Comando '%s' terminado", args.comando)


if __name__ == "__main__":
    main()
