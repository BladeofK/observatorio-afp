# Plan de desarrollo

Duración estimada: **4 semanas** con dedicación parcial. Cada fase termina con algo que
funciona y se puede mostrar. Si el tiempo apremia, las fases 0 a 4 ya forman un proyecto
completo para el portafolio.

> Regla de oro: **la fase 0 va primero, siempre.** No se crea ningún recurso que cobre antes de
> tener el blindaje de costos activo.

---

## Fase 0: Cuenta y blindaje de costos (día 1)

- [x] Crear el proyecto GCP (sin organización) y vincular la cuenta de facturación.
- [x] Crear un **proyecto aparte, sin facturación**, solo para la API key de Gemini (AI Studio).
- [x] Revisar la moneda de la cuenta de facturación (CLP) y ajustar `terraform.tfvars`.
- [x] Aplicar **solo** el blindaje con `terraform apply -target=...` (comando exacto en
      [blindaje-costos.md](blindaje-costos.md#orden-de-despliegue-fase-0)).
- [x] Probar la cadena alerta → Pub/Sub → función con un gasto simulado bajo el presupuesto.
- [ ] (Opcional) Probar el corte real con un gasto simulado sobre el presupuesto: desvincula
      la facturación y hay que volver a vincularla a mano.

**Término:** presupuesto, alertas, cuota de BigQuery y corte automático activos y probados.

## Fase 1: Explorar fuentes y ETL local (días 2–5)

- [x] Descargar los archivos de valor cuota y **confirmar el formato real**: encabezado de dos
      filas, un bloque por año, bloque final de valores provisorios y `fecconf` leído del sitio.
- [x] Ingesta de indicadores desde mindicador.cl (UF y dólar), con reintentos ante cortes.
- [x] Parseo a formato largo y reglas de calidad (`etl/calidad.py`).
- [x] Tests unitarios de parsers y calidad con un extracto real en `tests/fixtures/`.
- [x] `python -m observatorio.etl.main probar --desde 2022-01-01`: 62 370 filas de valor cuota
      e indicadores 2022–2026 validados sin errores.

**Término:** `uv run pytest` en verde y el ETL imprime filas válidas en local, sin GCP.

## Fase 2: Medallón en BigQuery (días 6–10)

- [x] `terraform apply` de datasets, bucket y cuentas de servicio.
- [x] `python -m observatorio.etl.main setup` crea tablas bronze y silver (DDL).
- [x] Carga a GCS y bronze con load jobs.
- [x] `MERGE` bronze → silver; idempotencia probada: tras recargar, silver sigue con 87 955
      filas y 0 duplicados.
- [x] Tablas gold con rentabilidad nominal y real (verificada a mano contra silver).
- [x] Carga histórica desde 2020-01-01 (casi 7 años).
- [x] Bytes escaneados: 350 MiB en el día de la carga completa (0,03 % del TiB gratuito);
      máximo 30 MiB por consulta.

**Término:** `python -m observatorio.etl.main diario` deja gold poblado, y repetirlo no
cambia los conteos.

## Fase 3: Despliegue del ETL (días 11–13)

- [ ] Build de la imagen y push a Artifact Registry.
- [ ] Cloud Run Job + Cloud Scheduler diario vía Terraform.
- [ ] Logs estructurados (JSON) para verlos filtrados en Cloud Logging.

**Término:** el job corre solo cada mañana y gold amanece actualizado.

## Fase 4: API y LLM (días 14–19)

- [ ] Endpoints de lectura con consultas parametrizadas.
- [ ] `/preguntar` con las 7 barreras del diseño y tests de cada barrera.
- [ ] Límite de solicitudes por IP y tope diario de preguntas.
- [ ] Despliegue en Cloud Run (`min=0`, `max=1`).
- [ ] Probar preguntas maliciosas: `DROP TABLE`, leer silver, consultas sin límite.

**Término:** API pública documentada en `/docs`; el LLM responde preguntas reales y rechaza las
maliciosas.

## Fase 5: Calidad profesional (días 20–23)

- [ ] GitHub Actions: lint + tests en cada push (ya incluido en `ci.yml`).
- [ ] Despliegue automático con Workload Identity Federation (sin llaves JSON).
- [ ] README final: diagrama, GIF de demo, decisiones técnicas y costos reales del mes.
- [ ] Badge de CI y enlace a la API en vivo.

## Fase 6: Extras opcionales (plus de la oferta)

- [ ] Frontend en **Angular** con gráficos y caja de preguntas, en Firebase Hosting.
- [ ] Comisiones por AFP como nueva fuente (silver + gold).
- [ ] Migrar las transformaciones SQL a **Dataform**.
- [ ] Resumen mensual redactado por el LLM y guardado en gold.

---

## Cómo contarlo en una entrevista

1. **Problema**: datos públicos de AFP dispersos y difíciles de comparar.
2. **Arquitectura**: Medallón; por qué bronze guarda el crudo y permite reprocesar.
3. **Ingeniería**: idempotencia con `MERGE`, particionado mensual, load jobs gratuitos.
4. **IA responsable**: siete barreras para que un LLM consulte una base de datos de forma segura.
5. **Criterio de costos**: costo real de USD 0 y límites duros que lo garantizan.
