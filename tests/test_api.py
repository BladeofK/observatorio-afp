"""Tests de la API que no requieren GCP ni Gemini."""

from fastapi.testclient import TestClient

from observatorio.api.main import app
from observatorio.config import get_settings

cliente = TestClient(app)


def test_salud():
    assert cliente.get("/salud").json() == {"estado": "ok"}


def test_fondo_invalido_es_422():
    assert cliente.get("/fondos/ranking", params={"fondo": "Z"}).status_code == 422


def test_preguntar_sin_gemini_responde_503(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    respuesta = cliente.post("/preguntar", json={"pregunta": "¿Qué AFP rinde más?"})
    assert respuesta.status_code == 503
    assert "no está configurado" in respuesta.json()["detail"]


def test_pregunta_muy_corta_es_422():
    assert cliente.post("/preguntar", json={"pregunta": "a"}).status_code == 422
