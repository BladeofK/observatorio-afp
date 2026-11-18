-- Bronze → silver para indicadores. Misma lógica idempotente que valor cuota.
-- mindicador.cl entrega la fecha como '2024-01-01T03:00:00.000Z' (medianoche en Chile):
-- los primeros 10 caracteres son la fecha local.

MERGE `$proyecto.$silver.indicadores` AS t
USING (
  WITH tipado AS (
    SELECT
      SAFE.PARSE_DATE('%Y-%m-%d', SUBSTR(TRIM(fecha), 1, 10)) AS fecha,
      LOWER(TRIM(indicador)) AS indicador,
      CAST(ROUND(SAFE_CAST(valor AS FLOAT64), 4) AS NUMERIC) AS valor,
      ingesta_ts
    FROM `$proyecto.$bronze.indicadores_raw`
    WHERE fecha_ingesta >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
  )
  SELECT *
  FROM tipado
  WHERE fecha IS NOT NULL AND valor IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY fecha, indicador ORDER BY ingesta_ts DESC) = 1
) AS s
ON t.fecha = s.fecha AND t.indicador = s.indicador
WHEN MATCHED AND t.valor IS DISTINCT FROM s.valor THEN
  UPDATE SET valor = s.valor, ingesta_ts = s.ingesta_ts
WHEN NOT MATCHED THEN
  INSERT (fecha, indicador, valor, ingesta_ts)
  VALUES (s.fecha, s.indicador, s.valor, s.ingesta_ts);
