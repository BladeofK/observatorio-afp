"""Reglas de calidad de datos aplicadas antes de pasar de bronze a silver.

Las reglas críticas detienen el pipeline; las advertencias solo quedan en el log.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from observatorio.etl.normalizar import a_fecha, a_numero, a_numero_chileno, nombre_afp

AFP_ESPERADAS = {"CAPITAL", "CUPRUM", "HABITAT", "MODELO", "PLANVITAL", "PROVIDA", "UNO"}
VARIACION_DIARIA_MAXIMA = 0.15


@dataclass
class Reporte:
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores


class Duplicados:
    """Cuenta apariciones por clave y los valores distintos vistos en cada una.

    - Duplicado exacto (misma clave, mismo valor): advertencia; silver deduplica.
      Ocurre en la práctica: mindicador.cl repite el dólar del 2022-04-19.
    - Duplicado contradictorio (misma clave, valores distintos): error.
    """

    def __init__(self) -> None:
        self.conteo: Counter[tuple] = Counter()
        self.valores: defaultdict[tuple, set[Decimal]] = defaultdict(set)

    def agregar(self, clave: tuple, valor: Decimal) -> None:
        self.conteo[clave] += 1
        self.valores[clave].add(valor)

    def reportar(self, nombre_clave: str, reporte: Reporte) -> None:
        repetidas = [clave for clave, veces in self.conteo.items() if veces > 1]
        contradictorias = sum(len(self.valores[clave]) > 1 for clave in repetidas)
        exactas = len(repetidas) - contradictorias
        if contradictorias:
            reporte.errores.append(
                f"{contradictorias} claves {nombre_clave} duplicadas con valores distintos"
            )
        if exactas:
            reporte.advertencias.append(
                f"{exactas} claves {nombre_clave} duplicadas con el mismo valor"
            )


def validar_valor_cuota(filas: list[dict[str, str]], hoy: date | None = None) -> Reporte:
    hoy = hoy or date.today()
    reporte = Reporte()
    duplicados = Duplicados()
    series: dict[tuple[str, str], dict[date, float]] = defaultdict(dict)

    for numero, fila in enumerate(filas, start=1):
        fecha = a_fecha(fila.get("fecha", ""))
        valor = a_numero_chileno(fila.get("valor_cuota", ""))
        afp = nombre_afp(fila.get("afp", ""))
        fondo = (fila.get("fondo") or "").strip()

        if fecha is None or valor is None or not afp or not fondo:
            reporte.errores.append(f"Fila {numero}: campo nulo o ilegible: {fila}")
            continue
        if valor <= 0:
            reporte.errores.append(f"Fila {numero}: valor cuota no positivo ({valor})")
        if fecha > hoy:
            reporte.errores.append(f"Fila {numero}: fecha futura ({fecha})")

        duplicados.agregar((fecha, afp, fondo), valor)
        series[(afp, fondo)][fecha] = float(valor)

    duplicados.reportar("(fecha, afp, fondo)", reporte)

    for (afp, fondo), puntos in series.items():
        ordenados = sorted(puntos.items())
        for (_, anterior), (fecha, actual) in zip(ordenados, ordenados[1:], strict=False):
            if anterior and abs(actual / anterior - 1) > VARIACION_DIARIA_MAXIMA:
                reporte.advertencias.append(
                    f"{afp} fondo {fondo}: variación > {VARIACION_DIARIA_MAXIMA:.0%} el {fecha}"
                )

    if duplicados.conteo:
        ultima = max(fecha for fecha, _, _ in duplicados.conteo)
        presentes = {afp for fecha, afp, _ in duplicados.conteo if fecha == ultima}
        faltantes = AFP_ESPERADAS - presentes
        if faltantes:
            reporte.advertencias.append(
                f"Faltan AFP en la última fecha ({ultima}): {sorted(faltantes)}"
            )

    return reporte


def validar_indicadores(filas: list[dict[str, str]], hoy: date | None = None) -> Reporte:
    hoy = hoy or date.today()
    reporte = Reporte()
    duplicados = Duplicados()

    for numero, fila in enumerate(filas, start=1):
        fecha = a_fecha(fila.get("fecha", ""))
        valor = a_numero(fila.get("valor", ""))
        indicador = fila.get("indicador", "")
        if fecha is None or valor is None or not indicador:
            reporte.errores.append(f"Fila {numero}: campo nulo o ilegible: {fila}")
            continue
        if valor <= 0:
            reporte.errores.append(f"Fila {numero}: valor no positivo ({valor})")
        if fecha > hoy:
            reporte.errores.append(f"Fila {numero}: fecha futura ({fecha})")
        duplicados.agregar((fecha, indicador), valor)

    duplicados.reportar("(fecha, indicador)", reporte)
    return reporte
