-- Bronze → silver para valor cuota. Idempotente: reejecutarlo no duplica filas.
-- Solo lee las particiones de bronze de los últimos 2 días (filtro constante = poda de
-- particiones = pocos bytes escaneados). Para reprocesar todo, ampliar el intervalo.
-- La conversión equivale a observatorio/etl/normalizar.py: mantener ambas alineadas.

MERGE `$proyecto.$silver.valor_cuota` AS t
USING (
  WITH tipado AS (
    SELECT
      COALESCE(
        SAFE.PARSE_DATE('%Y-%m-%d', TRIM(fecha)),
        SAFE.PARSE_DATE('%d-%m-%Y', TRIM(fecha)),
        SAFE.PARSE_DATE('%d/%m/%Y', TRIM(fecha))
      ) AS fecha,
      REGEXP_REPLACE(
        REGEXP_REPLACE(UPPER(NORMALIZE(afp, NFKD)), r'[^A-Z]', ''), r'^AFP', ''
      ) AS afp,
      TRIM(fondo) AS fondo,
      SAFE_CAST(REPLACE(REPLACE(TRIM(valor_cuota), '.', ''), ',', '.') AS NUMERIC) AS valor_cuota,
      SAFE_CAST(REPLACE(REPLACE(TRIM(patrimonio), '.', ''), ',', '.') AS NUMERIC) AS patrimonio,
      COALESCE(NULLIF(TRIM(estado), ''), 'confirmado') AS estado,
      ingesta_ts
    FROM `$proyecto.$bronze.valor_cuota_raw`
    WHERE fecha_ingesta >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
  )
  SELECT *
  FROM tipado
  WHERE fecha IS NOT NULL AND valor_cuota IS NOT NULL AND afp != ''
  -- Si el mismo dato llegó varias veces: gana el confirmado sobre el provisorio y, entre
  -- iguales, la ingesta más reciente.
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY fecha, afp, fondo
    ORDER BY IF(estado = 'confirmado', 0, 1), ingesta_ts DESC
  ) = 1
) AS s
ON t.fecha = s.fecha AND t.afp = s.afp AND t.fondo = s.fondo
-- Un valor provisorio nunca reemplaza a uno ya confirmado.
WHEN MATCHED
  AND NOT (t.estado = 'confirmado' AND s.estado = 'provisorio')
  AND (
    t.valor_cuota IS DISTINCT FROM s.valor_cuota
    OR t.patrimonio IS DISTINCT FROM s.patrimonio
    OR t.estado IS DISTINCT FROM s.estado
  ) THEN
  UPDATE SET
    valor_cuota = s.valor_cuota,
    patrimonio = s.patrimonio,
    estado = s.estado,
    ingesta_ts = s.ingesta_ts
WHEN NOT MATCHED THEN
  INSERT (fecha, afp, fondo, valor_cuota, patrimonio, estado, ingesta_ts)
  VALUES (s.fecha, s.afp, s.fondo, s.valor_cuota, s.patrimonio, s.estado, s.ingesta_ts);
