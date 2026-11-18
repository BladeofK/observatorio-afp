from datetime import date

from observatorio.etl.calidad import validar_indicadores, validar_valor_cuota

HOY = date(2025, 6, 30)


def fila(fecha="2025-01-02", afp="MODELO", fondo="A", valor="100,00"):
    return {"fecha": fecha, "afp": afp, "fondo": fondo, "valor_cuota": valor, "patrimonio": "1"}


def test_lote_valido_sin_errores():
    reporte = validar_valor_cuota([fila(), fila(fecha="2025-01-03", valor="100,50")], hoy=HOY)
    assert reporte.ok


def test_detecta_nulos_negativos_futuros_y_duplicados():
    filas = [
        fila(valor=""),
        fila(fecha="2025-01-05", valor="-1,0"),
        fila(fecha="2030-01-01"),
        fila(fecha="2025-01-10"),
        fila(fecha="2025-01-10"),
    ]
    errores = " | ".join(validar_valor_cuota(filas, hoy=HOY).errores)
    assert "nulo" in errores
    assert "no positivo" in errores
    assert "futura" in errores
    assert "duplicadas" in errores


def test_salto_brusco_es_advertencia_no_error():
    filas = [fila(valor="100,00"), fila(fecha="2025-01-03", valor="150,00")]
    reporte = validar_valor_cuota(filas, hoy=HOY)
    assert reporte.ok
    assert any("variación" in a for a in reporte.advertencias)


def test_advierte_afp_faltantes():
    reporte = validar_valor_cuota([fila()], hoy=HOY)
    assert any("Faltan AFP" in a for a in reporte.advertencias)


def test_indicadores():
    buenas = [{"indicador": "uf", "fecha": "2025-01-01T03:00:00.000Z", "valor": "38419.17"}]
    assert validar_indicadores(buenas, hoy=HOY).ok
    malas = [{"indicador": "uf", "fecha": "x", "valor": "1"}]
    assert not validar_indicadores(malas, hoy=HOY).ok
