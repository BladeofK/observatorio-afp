-- Verificaciones de calidad sobre silver. Si un ASSERT falla, el job termina con error
-- y gold no se recalcula con datos malos.

ASSERT NOT EXISTS (
  SELECT 1 FROM `$proyecto.$silver.valor_cuota`
  GROUP BY fecha, afp, fondo HAVING COUNT(*) > 1
) AS 'silver.valor_cuota tiene claves (fecha, afp, fondo) duplicadas';

ASSERT NOT EXISTS (
  SELECT 1 FROM `$proyecto.$silver.valor_cuota` WHERE valor_cuota <= 0
) AS 'silver.valor_cuota tiene valores cuota no positivos';

ASSERT NOT EXISTS (
  SELECT 1 FROM `$proyecto.$silver.indicadores`
  GROUP BY fecha, indicador HAVING COUNT(*) > 1
) AS 'silver.indicadores tiene claves (fecha, indicador) duplicadas';
