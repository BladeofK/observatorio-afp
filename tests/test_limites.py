from datetime import date

import pytest

from observatorio.api.limites import Limitador, LimiteExcedido


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_limite_por_minuto_por_ip():
    reloj = Reloj()
    limitador = Limitador(max_por_minuto_ip=2, max_diario=100, reloj=reloj)
    limitador.registrar("1.1.1.1")
    limitador.registrar("1.1.1.1")
    with pytest.raises(LimiteExcedido):
        limitador.registrar("1.1.1.1")
    limitador.registrar("2.2.2.2")  # Otra IP no se ve afectada
    reloj.t = 61
    limitador.registrar("1.1.1.1")  # Pasó el minuto


def test_limite_diario_global_y_reinicio():
    limitador = Limitador(max_por_minuto_ip=100, max_diario=2, reloj=Reloj())
    hoy, manana = date(2025, 1, 1), date(2025, 1, 2)
    limitador.registrar("a", hoy)
    limitador.registrar("b", hoy)
    with pytest.raises(LimiteExcedido):
        limitador.registrar("c", hoy)
    limitador.registrar("c", manana)
