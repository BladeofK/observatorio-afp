# Plan de desarrollo

Duración estimada: **4 semanas** con dedicación parcial. Cada fase termina con algo que
funciona y se puede mostrar. Si el tiempo apremia, las fases 0 a 4 ya forman un proyecto
completo para el portafolio.

> Regla de oro: **la fase 0 va primero, siempre.** No se crea ningún recurso que cobre antes de
> tener el blindaje de costos activo.

---

## Fase 0: Cuenta y blindaje de costos (día 1)

- [ ] Crear el proyecto GCP `observatorio-afp-<sufijo>` y vincular la cuenta de facturación.
- [ ] Crear un **proyecto aparte, sin facturación**, solo para la API key de Gemini (AI Studio).
- [ ] Revisar la moneda de la cuenta de facturación (USD o CLP) y ajustar `terraform.tfvars`.
- [ ] Aplicar **solo** el blindaje con `terraform apply -target=...` (comando exacto en
      [blindaje-costos.md](blindaje-costos.md#orden-de-despliegue-fase-0)).
- [ ] Probar el corte: publicar un mensaje falso en el tópico (ver
      [blindaje-costos.md](blindaje-costos.md#probar-el-corte)) en un proyecto de prueba.

**Término:** presupuesto, alertas, cuota de BigQuery y corte automático activos y probados.

## Fase 1: Explorar fuentes y ETL local (días 2–5)

- [ ] Descargar manualmente los archivos de valor cuota y **confirmar el formato real**
      (separador, decimales, encabezados). Ajustar `etl/fuentes/valor_cuota.py` y su fixture.
- [ ] Ingesta de indicadores desde mindicador.cl (UF y dólar).
- [ ] Parseo a formato largo y reglas de calidad (`etl/calidad.py`).
- [ ] Tests unitarios de parsers y calidad con archivos de ejemplo en `tests/fixtures/`.

**Término:** `uv run pytest` en verde y el ETL imprime filas válidas en local, sin GCP.

## Fase 2: Medallón en BigQuery (días 6–10)

- [ ] `terraform apply` de datasets, bucket y cuentas de servicio.
- [ ] `python -m observatorio.etl.main setup` crea tablas bronze y silver (DDL).
- [ ] Carga a GCS y bronze con load jobs.
- [ ] `MERGE` bronze → silver; probar idempotencia ejecutando dos veces el mismo día.
- [ ] Tablas gold con rentabilidad nominal y real.
- [ ] Carga histórica (backfill) de al menos 3 años.
- [ ] Revisar en "Información de ejecución" de BigQuery los bytes escaneados por consulta.

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
