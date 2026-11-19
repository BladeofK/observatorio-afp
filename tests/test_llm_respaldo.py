"""Respaldo entre modelos de Gemini, sin llamar a la API real."""

import time

import pytest

from observatorio.config import get_settings
from observatorio.llm import texto_a_sql
from observatorio.llm.texto_a_sql import LLMNoDisponible, _generar


class ErrorGemini(Exception):
    def __init__(self, code, message="error simulado"):
        super().__init__(message)
        self.code, self.message = code, message


@pytest.fixture(autouse=True)
def configuracion(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key", "clave-de-prueba")
    monkeypatch.setattr(s, "gemini_model", "principal")
    monkeypatch.setattr(s, "gemini_modelos_respaldo", "respaldo1, respaldo2")
    monkeypatch.setattr(s, "gemini_timeout_s", 1)


def llamador(*resultados):
    """Devuelve una función que responde (o falla) según el orden dado y anota los modelos."""
    usados = []

    def llamar(modelo, prompt):
        usados.append(modelo)
        resultado = resultados[len(usados) - 1]
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    return llamar, usados


def test_usa_el_principal_si_responde():
    llamar, usados = llamador("ok")
    assert _generar("p", time.monotonic() + 60, llamar) == "ok"
    assert usados == ["principal"]


def test_pasa_al_respaldo_si_el_principal_esta_saturado():
    llamar, usados = llamador(ErrorGemini(503), ErrorGemini(429), "ok")
    assert _generar("p", time.monotonic() + 60, llamar) == "ok"
    assert usados == ["principal", "respaldo1", "respaldo2"]


def test_falla_claro_si_ninguno_responde():
    llamar, _ = llamador(ErrorGemini(503), ErrorGemini(503), ErrorGemini(429))
    with pytest.raises(LLMNoDisponible, match="429"):
        _generar("p", time.monotonic() + 60, llamar)


def test_respeta_el_presupuesto_de_tiempo():
    llamar, usados = llamador("ok")
    with pytest.raises(LLMNoDisponible):
        _generar("p", time.monotonic(), llamar)  # presupuesto ya agotado
    assert usados == []


def test_lista_de_modelos_sin_repetidos(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_modelos_respaldo", "principal,respaldo1")
    assert texto_a_sql._modelos() == ["principal", "respaldo1"]
