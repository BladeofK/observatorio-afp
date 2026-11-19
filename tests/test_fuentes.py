import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from observatorio.etl.fuentes import indicadores, valor_cuota
from observatorio.etl.main import inicio_recarga_diaria
from observatorio.etl.normalizar import a_fecha, a_numero_chileno, nombre_afp

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def filas_valor_cuota():
    # Extracto real de spensiones.cl: bloque 2010 (5 AFP), bloque 2026 confirmado (7 AFP)
    # y bloque de valores provisorios.
    return valor_cuota.parsear((FIXTURES / "valor_cuota_A.csv").read_bytes(), "A")


def test_parsea_todos_los_bloques(filas_valor_cuota):
    # 2010: 2 días x 5 AFP | 2026 confirmado: 2 x 7 | provisorio: 3 x 7
    assert len(filas_valor_cuota) == 10 + 14 + 21


def test_primera_fila_tal_cual_viene(filas_valor_cuota):
    assert filas_valor_cuota[0] == {
        "fondo": "A",
        "afp": "CAPITAL",
        "fecha": "2010-01-01",
        "valor_cuota": "23.050,39",
        "patrimonio": "3068119298249",
        "estado": "confirmado",
    }


def test_las_afp_cambian_segun_el_anio(filas_valor_cuota):
    afp_2010 = {f["afp"] for f in filas_valor_cuota if f["fecha"].startswith("2010")}
    afp_2026 = {f["afp"] for f in filas_valor_cuota if f["fecha"].startswith("2026")}
    assert afp_2010 == {"CAPITAL", "CUPRUM", "HABITAT", "PLANVITAL", "PROVIDA"}
    assert afp_2026 == afp_2010 | {"MODELO", "UNO"}


def test_marca_valores_provisorios(filas_valor_cuota):
    provisorias = {f["fecha"] for f in filas_valor_cuota if f["estado"] == "provisorio"}
    assert provisorias == {"2026-11-01", "2026-11-02", "2026-11-03"}


def test_rechaza_archivo_sin_encabezado():
    with pytest.raises(ValueError):
        valor_cuota.parsear(b"esto no es el archivo\n", "A")


def test_parsea_indicadores_mindicador():
    contenido = json.dumps(
        {"codigo": "uf", "serie": [{"fecha": "2025-01-01T03:00:00.000Z", "valor": 38419.17}]}
    ).encode()
    filas = indicadores.parsear(contenido, "uf")
    assert filas == [{"indicador": "uf", "fecha": "2025-01-01T03:00:00.000Z", "valor": "38419.17"}]
    assert a_fecha(filas[0]["fecha"]).isoformat() == "2025-01-01"


def test_normalizacion():
    assert a_numero_chileno("61.234,56") == Decimal("61234.56")
    assert a_numero_chileno("7425745000772") == Decimal("7425745000772")
    assert a_numero_chileno("abc") is None
    assert a_fecha("02/01/2025").isoformat() == "2025-01-02"
    assert nombre_afp("AFP Plan Vital") == "PLANVITAL"
    assert nombre_afp("Hábitat") == "HABITAT"


@pytest.mark.parametrize(
    ("hoy", "esperado"),
    [(date(2026, 11, 18), date(2026, 10, 1)), (date(2026, 1, 5), date(2025, 12, 1))],
)
def test_recarga_diaria_desde_el_mes_anterior(hoy, esperado):
    assert inicio_recarga_diaria(hoy) == esperado
