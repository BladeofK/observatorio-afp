import httpx
import pytest

from observatorio.etl import fuentes


def respuestas(*secuencia):
    """Simula httpx.get devolviendo (o lanzando) cada elemento en orden."""
    llamadas = []

    def falso_get(url, **kwargs):
        llamadas.append(url)
        item = secuencia[len(llamadas) - 1]
        if isinstance(item, Exception):
            raise item
        return httpx.Response(item, content=b"ok", request=httpx.Request("GET", url))

    return falso_get, llamadas


def test_reintenta_cortes_y_errores_5xx(monkeypatch):
    falso_get, llamadas = respuestas(httpx.ReadTimeout("lento"), 503, 200)
    monkeypatch.setattr(fuentes.httpx, "get", falso_get)
    assert fuentes.descargar("https://x", espera_inicial=0) == b"ok"
    assert len(llamadas) == 3


def test_no_reintenta_errores_4xx(monkeypatch):
    falso_get, llamadas = respuestas(404)
    monkeypatch.setattr(fuentes.httpx, "get", falso_get)
    with pytest.raises(httpx.HTTPStatusError):
        fuentes.descargar("https://x", espera_inicial=0)
    assert len(llamadas) == 1


def test_se_rinde_tras_el_ultimo_intento(monkeypatch):
    falso_get, llamadas = respuestas(*[httpx.ConnectError("caído")] * fuentes.INTENTOS)
    monkeypatch.setattr(fuentes.httpx, "get", falso_get)
    with pytest.raises(httpx.ConnectError):
        fuentes.descargar("https://x", espera_inicial=0)
    assert len(llamadas) == fuentes.INTENTOS
