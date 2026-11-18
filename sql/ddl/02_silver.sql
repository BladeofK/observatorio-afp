-- Silver: datos tipados, normalizados y únicos.
-- Partición MENSUAL: con pocas filas por día, una partición diaria crearía miles de
-- particiones diminutas. El cluster por afp/fondo reduce los bytes leídos al filtrar.

CREATE TABLE IF NOT EXISTS `$proyecto.$silver.valor_cuota` (
  fecha       DATE    NOT NULL,
  afp         STRING  NOT NULL,
  fondo       STRING  NOT NULL,
  valor_cuota NUMERIC NOT NULL,
  patrimonio  NUMERIC,
  ingesta_ts  TIMESTAMP
)
PARTITION BY DATE_TRUNC(fecha, MONTH)
CLUSTER BY afp, fondo
OPTIONS (description = 'Valor cuota diario por AFP y fondo. Clave: (fecha, afp, fondo)');

CREATE TABLE IF NOT EXISTS `$proyecto.$silver.indicadores` (
  fecha      DATE    NOT NULL,
  indicador  STRING  NOT NULL,
  valor      NUMERIC NOT NULL,
  ingesta_ts TIMESTAMP
)
PARTITION BY DATE_TRUNC(fecha, MONTH)
CLUSTER BY indicador
OPTIONS (description = 'Indicadores diarios (uf, dolar). Clave: (fecha, indicador)');
