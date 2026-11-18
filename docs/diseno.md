# Diseño técnico

## 1. Objetivo

Responder con datos públicos y actualizados preguntas como:

- ¿Qué AFP tuvo la mejor rentabilidad real en el fondo C en los últimos 12 meses?
- ¿Cómo evolucionó el valor cuota del fondo A de AFP Modelo este año?
- ¿Cuánto rindió el fondo E descontada la inflación (UF)?

## 2. Componentes

| Componente | Servicio GCP | Responsabilidad |
|---|---|---|
| Orquestación | Cloud Scheduler | Dispara el job ETL una vez al día |
| ETL | Cloud Run **Job** | Descarga, guarda crudo, valida, carga y transforma |
| Data lake | Cloud Storage | Archivos crudos inmutables (bronze), reprocesables |
| Data warehouse | BigQuery | Capas bronze, silver y gold |
| API | Cloud Run **Service** | Endpoints REST de lectura sobre gold y endpoint LLM |
| LLM | Gemini API (AI Studio) | Traduce preguntas a SQL y redacta respuestas |
| Secretos | Secret Manager | API key de Gemini |
| Imágenes | Artifact Registry | Imagen Docker única (API + job) |
| Control de costos | Billing Budgets + Pub/Sub + Cloud Function | Alertas y corte automático de facturación |

## 3. Flujo del ETL (job diario)

1. **Extraer**: descarga el archivo de cada fuente (valor cuota por tipo de fondo, UF, dólar).
2. **Bronze, GCS**: guarda el archivo tal como llegó en
   `gs://<bucket>/bronze/<fuente>/fecha_ingesta=YYYY-MM-DD/<archivo>`. Es la fuente de verdad:
   si cambia la lógica, se reprocesa desde aquí sin volver a descargar.
3. **Bronze, BigQuery**: parsea a formato largo con **todas las columnas como STRING** y
   metadatos de ingesta. Carga con *load job* (gratis), nunca con *streaming insert* (pagado).
4. **Validar**: reglas de calidad sobre lo parseado (ver §6). Si fallan reglas críticas, el job
   termina con error y no toca silver.
5. **Silver**: `MERGE` desde bronze con `SAFE_CAST`, normalización de nombres de AFP y
   deduplicación (gana la ingesta más reciente). Idempotente: reejecutar un día no duplica nada.
6. **Gold**: `CREATE OR REPLACE TABLE` de las tablas analíticas a partir de silver.

## 4. Modelo de datos

### Bronze (crudo, append-only)

`bronze.valor_cuota_raw`

| Columna | Tipo | Nota |
|---|---|---|
| fecha_ingesta | DATE | Partición |
| ingesta_ts | TIMESTAMP | Momento de la carga |
| archivo_origen | STRING | Ruta en GCS |
| fondo | STRING | A, B, C, D, E |
| afp | STRING | Como viene en la fuente |
| fecha | STRING | Sin convertir |
| valor_cuota | STRING | Sin convertir (coma decimal) |
| patrimonio | STRING | Sin convertir |

`bronze.indicadores_raw`: `fecha_ingesta`, `ingesta_ts`, `archivo_origen`, `indicador`,
`fecha`, `valor`, todos los datos en STRING.

### Silver (limpio, tipado, único)

`silver.valor_cuota`: `fecha DATE`, `afp STRING`, `fondo STRING`, `valor_cuota NUMERIC`,
`patrimonio NUMERIC`, `ingesta_ts TIMESTAMP`.
Clave única: `(fecha, afp, fondo)`. Partición mensual `DATE_TRUNC(fecha, MONTH)` (evita miles de
particiones diminutas) y cluster por `afp, fondo`.

`silver.indicadores`: `fecha DATE`, `indicador STRING`, `valor NUMERIC`, `ingesta_ts`.
Clave única `(fecha, indicador)`.

### Gold (listo para consumo)

`gold.rentabilidad_mensual`: una fila por mes, AFP y fondo.

| Columna | Definición |
|---|---|
| mes | Primer día del mes |
| afp, fondo | |
| valor_cuota_cierre | Último valor cuota disponible del mes |
| rent_nominal_mes | `vc / vc_mes_anterior - 1` |
| rent_nominal_12m | `vc / vc_hace_12_meses - 1` |
| rent_real_12m | `(vc / vc_12) / (uf / uf_12) - 1`, deflactada con UF de cierre de mes |

`gold.ranking_fondos`: último mes disponible, ranking de AFP por `rent_real_12m` en cada fondo.

`gold.indicadores_mensual`: cierre mensual de UF y dólar.

> **Riesgo de dominio:** la reforma previsional de 2025 contempla reemplazar gradualmente los
> multifondos por fondos generacionales. `fondo` es STRING libre (no un ENUM) para soportar
> nuevos tipos de fondo sin migrar el esquema.

## 5. API REST

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/salud` | Healthcheck |
| GET | `/fondos/rentabilidad?fondo=C&afp=MODELO&desde=2025-01-01` | Serie mensual de rentabilidad |
| GET | `/fondos/ranking?fondo=C` | Ranking del último mes por rentabilidad real 12m |
| GET | `/indicadores/{codigo}?desde=` | Serie mensual de UF o dólar |
| POST | `/preguntar` | `{"pregunta": "..."}` → SQL generado, filas y respuesta redactada |

Todas las consultas usan **parámetros** de BigQuery (nunca concatenación de strings) y
`maximum_bytes_billed`.

## 6. Calidad de datos

| Regla | Severidad |
|---|---|
| Sin nulos en fecha, AFP, fondo y valor | Crítica |
| Valor cuota > 0 | Crítica |
| Fechas no futuras | Crítica |
| Sin duplicados `(fecha, afp, fondo)` en el lote | Crítica |
| Variación diaria del valor cuota < 15 % | Advertencia (posible error de la fuente) |
| Las 7 AFP presentes en la última fecha | Advertencia |

## 7. Diseño del LLM (`/preguntar`)

Flujo: pregunta → prompt con el **esquema de gold** → Gemini genera SQL → **barreras** →
dry run → ejecución → Gemini redacta la respuesta con las filas obtenidas.

Barreras, en capas (defensa en profundidad):

1. **Validación sintáctica con sqlglot**: una sola sentencia, solo `SELECT`/`WITH`; se rechaza
   cualquier `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE`, `DROP`, `ALTER`.
2. **Lista blanca de tablas**: solo tablas del dataset `gold`.
3. **`LIMIT` forzado**: si no viene, se agrega `LIMIT 100`; si viene mayor a 1000, se reduce.
4. **Dry run**: se estima el costo antes de ejecutar; si supera el tope, se rechaza.
5. **`maximum_bytes_billed`**: BigQuery aborta la consulta si escanearía más del tope.
6. **Permisos mínimos**: la cuenta de servicio de la API solo tiene `dataViewer` sobre `gold`.
   Aunque todo lo anterior fallara, no puede escribir ni leer otras capas.
7. **Límite de uso**: máximo N preguntas por IP por minuto y M preguntas diarias en total.

## 8. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Cloud Scheduler + Cloud Run Jobs | Cloud Composer (Airflow) | Composer cuesta cientos de USD al mes; para un pipeline diario basta un cron |
| Load jobs | Streaming inserts | Los load jobs son gratuitos; el streaming se cobra |
| SQL versionado en `sql/` | dbt / Dataform | Menos piezas para el MVP; Dataform queda como mejora (fase 6) |
| Gemini vía AI Studio | Vertex AI | AI Studio tiene capa gratuita real; Vertex AI cobra desde el primer uso |
| Partición mensual | Partición diaria | Pocos datos por día; la partición diaria generaría miles de particiones diminutas |
| Imagen Docker única | Dos imágenes | Menos espacio en Artifact Registry (0,5 GB gratis) y un solo build |
| Región us-central1 / multirregión US | southamerica-west1 (Santiago) | La capa gratuita de Storage solo aplica en regiones de EE. UU. |
