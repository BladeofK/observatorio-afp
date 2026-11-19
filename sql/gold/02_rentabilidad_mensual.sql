-- Gold: rentabilidad mensual y a 12 meses, nominal y real (deflactada con UF).
-- rent_real_12m = (vc / vc_hace_12m) / (uf / uf_hace_12m) - 1
-- Los LAG solo se usan si el mes anterior existe de verdad (sin huecos en la serie).
-- El mes en curso usa el último valor disponible, por lo que es un cierre parcial.
-- La UF se toma del MISMO día que el valor cuota de cierre (no del cierre del mes), para
-- que ambos lados de la deflactación correspondan a la misma fecha.

CREATE OR REPLACE TABLE `$proyecto.$gold.rentabilidad_mensual`
CLUSTER BY fondo, afp
OPTIONS (description = 'Rentabilidad nominal y real por AFP y fondo, por mes')
AS
WITH cierre AS (
  SELECT
    DATE_TRUNC(fecha, MONTH) AS mes,
    afp,
    fondo,
    MAX(fecha) AS fecha_cierre,
    ARRAY_AGG(valor_cuota ORDER BY fecha DESC LIMIT 1)[OFFSET(0)] AS vc
  FROM `$proyecto.$silver.valor_cuota`
  GROUP BY mes, afp, fondo
),
uf AS (
  SELECT fecha AS fecha_cierre, valor AS uf
  FROM `$proyecto.$silver.indicadores`
  WHERE indicador = 'uf'
),
con_rezagos AS (
  SELECT
    c.mes, c.afp, c.fondo, c.vc, u.uf,
    LAG(c.mes)     OVER w AS mes_1,
    LAG(c.vc)      OVER w AS vc_1,
    LAG(c.mes, 12) OVER w AS mes_12,
    LAG(c.vc, 12)  OVER w AS vc_12,
    LAG(u.uf, 12)  OVER w AS uf_12
  FROM cierre AS c
  LEFT JOIN uf AS u USING (fecha_cierre)
  WINDOW w AS (PARTITION BY c.afp, c.fondo ORDER BY c.mes)
)
SELECT
  mes,
  afp,
  fondo,
  vc AS valor_cuota_cierre,
  IF(mes_1 = DATE_SUB(mes, INTERVAL 1 MONTH),
     CAST(SAFE_DIVIDE(vc, vc_1) - 1 AS FLOAT64), NULL) AS rent_nominal_mes,
  IF(mes_12 = DATE_SUB(mes, INTERVAL 12 MONTH),
     CAST(SAFE_DIVIDE(vc, vc_12) - 1 AS FLOAT64), NULL) AS rent_nominal_12m,
  IF(mes_12 = DATE_SUB(mes, INTERVAL 12 MONTH),
     CAST(SAFE_DIVIDE(SAFE_DIVIDE(vc, vc_12), SAFE_DIVIDE(uf, uf_12)) - 1 AS FLOAT64),
     NULL) AS rent_real_12m
FROM con_rezagos;
