"""Punto de entrada del job ETL (Cloud Run Job o local).

Uso:
    python -m observatorio.etl.main probar                # descarga y valida, sin GCP
    python -m observatorio.etl.main setup                 # crea tablas bronze y silver
    python -m observatorio.etl.main ingestar              # carga bronze desde el mes anterior
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


def inicio_recarga_diaria(hoy: date) -> date:
    """Primer día del mes anterior.

    La Superintendencia publica valores provisorios y los confirma al mes siguiente. Recargar
    desde el mes anterior asegura que silver reemplace los provisorios por los confirmados.
    """
    primero_mes_actual = hoy.replace(day=1)
    return (primero_mes_actual - timedelta(days=1)).replace(day=1)

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
    fecconf = valor_cuota.obtener_fecconf()
    log.info("Fecha de corte de confirmación en la fuente: %s", fecconf)

    for fondo in valor_cuota.FONDOS:
        extraccion = valor_cuota.extraer(fondo, desde, hasta, fecconf)
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


def probar(desde: date, hasta: date) -> None:
    """Descarga y valida las fuentes SIN tocar GCP. Útil para revisar en local."""
    fecconf = valor_cuota.obtener_fecconf()
    log.info("Fecha de corte de confirmación en la fuente: %s", fecconf)
    for fondo in valor_cuota.FONDOS:
        filas = _en_rango(valor_cuota.extraer(fondo, desde, hasta, fecconf).filas, desde, hasta)
        reporte = calidad.validar_valor_cuota(filas)
        estados = {e: sum(f["estado"] == e for f in filas) for e in ("confirmado", "provisorio")}
        log.info(
            "valor_cuota fondo %s: %d filas %s, %d errores, %d advertencias",
            fondo, len(filas), estados, len(reporte.errores), len(reporte.advertencias),
        )
        _revisar(f"valor_cuota {fondo}", reporte)
    for indicador in indicadores.INDICADORES:
        for anio in range(desde.year, hasta.year + 1):
            filas = _en_rango(indicadores.extraer(indicador, anio).filas, desde, hasta)
            reporte = calidad.validar_indicadores(filas)
            log.info("%s %d: %d filas, %d errores", indicador, anio, len(filas),
                     len(reporte.errores))
            _revisar(f"{indicador} {anio}", reporte)


def main(argv: list[str] | None = None) -> None:
    _configurar_logs()
    parser = argparse.ArgumentParser(description="ETL Observatorio AFP")
    parser.add_argument(
        "comando", choices=["probar", "setup", "ingestar", "transformar", "diario"]
    )
    parser.add_argument("--desde", type=date.fromisoformat, default=None)
    parser.add_argument("--hasta", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)

    hasta = args.hasta or date.today()
    desde = args.desde or inicio_recarga_diaria(hasta)

    if args.comando == "probar":
        probar(desde, hasta)
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
