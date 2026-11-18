-- Gold: cierre mensual de cada indicador (último valor disponible del mes).

CREATE OR REPLACE TABLE `$proyecto.$gold.indicadores_mensual`
CLUSTER BY indicador
OPTIONS (description = 'Valor de cierre mensual de UF y dólar')
AS
SELECT
  DATE_TRUNC(fecha, MONTH) AS mes,
  indicador,
  ARRAY_AGG(valor ORDER BY fecha DESC LIMIT 1)[OFFSET(0)] AS valor_cierre
FROM `$proyecto.$silver.indicadores`
GROUP BY mes, indicador;
