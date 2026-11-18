-- Bronze: datos tal como llegan, todo en STRING. Solo se agregan filas (append-only).
-- Partición diaria por fecha de ingesta: el MERGE a silver solo lee las particiones recientes.
-- Las particiones expiran a los 400 días; el archivo original sigue en GCS para reprocesar.

CREATE TABLE IF NOT EXISTS `$proyecto.$bronze.valor_cuota_raw` (
  fecha_ingesta  DATE      NOT NULL,
  ingesta_ts     TIMESTAMP NOT NULL,
  archivo_origen STRING,
  fondo          STRING,
  afp            STRING,
  fecha          STRING,
  valor_cuota    STRING,
  patrimonio     STRING
)
PARTITION BY fecha_ingesta
OPTIONS (
  partition_expiration_days = 400,
  description = 'Valor cuota crudo desde la Superintendencia de Pensiones'
);

CREATE TABLE IF NOT EXISTS `$proyecto.$bronze.indicadores_raw` (
  fecha_ingesta  DATE      NOT NULL,
  ingesta_ts     TIMESTAMP NOT NULL,
  archivo_origen STRING,
  indicador      STRING,
  fecha          STRING,
  valor          STRING
)
PARTITION BY fecha_ingesta
OPTIONS (
  partition_expiration_days = 400,
  description = 'Indicadores económicos crudos desde mindicador.cl'
);
