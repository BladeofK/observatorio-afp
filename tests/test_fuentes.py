import json
from decimal import Decimal
from pathlib import Path

from observatorio.etl.fuentes import indicadores, valor_cuota
from observatorio.etl.normalizar import a_fecha, a_numero_chileno, nombre_afp

FIXTURES = Path(__file__).parent / "fixtures"


def test_parsea_valor_cuota_a_formato_largo():
    filas = valor_cuota.parsear((FIXTURES / "valor_cuota_A.csv").read_bytes(), "A")

    # 3 AFP el primer día + 2 el segundo (PlanVital viene vacío)
    assert len(filas) == 5
    assert filas[0] == {
        "fondo": "A",
        "afp": "CAPITAL",
        "fecha": "2025-01-02",
        "valor_cuota": "61.234,56",
        "patrimonio": "12.345.678.901",
    }
    assert {f["afp"] for f in filas if f["fecha"] == "2025-01-03"} == {"CAPITAL", "MODELO"}


def test_valor_cuota_acepta_latin1():
    contenido = "Fecha;HÁBITAT Valor Cuota\n2025-01-02;10,5\n".encode("latin-1")
    filas = valor_cuota.parsear(contenido, "C")
    assert filas[0]["afp"] == "HÁBITAT"


def test_parsea_indicadores_mindicador():
    contenido = json.dumps(
        {"codigo": "uf", "serie": [{"fecha": "2025-01-01T03:00:00.000Z", "valor": 38419.17}]}
    ).encode()
    filas = indicadores.parsear(contenido, "uf")
    assert filas == [{"indicador": "uf", "fecha": "2025-01-01T03:00:00.000Z", "valor": "38419.17"}]
    assert a_fecha(filas[0]["fecha"]).isoformat() == "2025-01-01"


def test_normalizacion():
    assert a_numero_chileno("61.234,56") == Decimal("61234.56")
    assert a_numero_chileno("abc") is None
    assert a_fecha("02/01/2025").isoformat() == "2025-01-02"
    assert nombre_afp("AFP Plan Vital") == "PLANVITAL"
    assert nombre_afp("Hábitat") == "HABITAT"
