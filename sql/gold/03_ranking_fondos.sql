-- Gold: ranking de AFP por rentabilidad real a 12 meses, en el último mes disponible.

CREATE OR REPLACE TABLE `$proyecto.$gold.ranking_fondos`
OPTIONS (description = 'Ranking de AFP por rentabilidad real 12m en cada fondo')
AS
WITH ultimo_mes AS (
  SELECT MAX(mes) AS mes
  FROM `$proyecto.$gold.rentabilidad_mensual`
  WHERE rent_real_12m IS NOT NULL
)
SELECT
  r.mes,
  r.fondo,
  RANK() OVER (PARTITION BY r.fondo ORDER BY r.rent_real_12m DESC) AS posicion,
  r.afp,
  r.rent_real_12m,
  r.rent_nominal_12m
FROM `$proyecto.$gold.rentabilidad_mensual` AS r
JOIN ultimo_mes AS u USING (mes)
WHERE r.rent_real_12m IS NOT NULL;
