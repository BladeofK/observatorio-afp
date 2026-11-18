# Blindaje de costos

Objetivo: que el proyecto **nunca** genere un cobro, aunque haya un bug, un bucle infinito o
alguien abuse de la API pública.

> ⚠️ En GCP un **presupuesto por sí solo no detiene el gasto**: solo envía alertas. Por eso este
> proyecto combina límites duros por servicio con un corte automático de facturación.

## Las 7 capas de protección

| # | Capa | Tipo | Dónde está |
|---|---|---|---|
| 1 | Cuota diaria de BigQuery: 10 GiB escaneados por día | **Límite duro** | `infra/terraform/quotas.tf` |
| 2 | `maximum_bytes_billed` en cada consulta (100 MiB) | **Límite duro** | `src/observatorio/bq.py` |
| 3 | Cloud Run con `min=0`, `max=1` instancia y CPU solo en requests | **Límite duro** | `infra/terraform/cloudrun.tf` |
| 4 | Gemini con API key de un proyecto **sin facturación** | **Límite duro** | Manual (fase 0) |
| 5 | Límite de preguntas por IP y diario en la API | **Límite duro** | `src/observatorio/api/limites.py` |
| 6 | Presupuesto con alertas al 25 %, 50 %, 90 % y 100 % | Aviso | `infra/terraform/budget.tf` |
| 7 | Corte automático: desvincula la facturación al llegar al 100 % | **Interruptor** | `infra/terraform/corte_facturacion.tf` |

### Por qué estos números son seguros

- **BigQuery**: 10 GiB/día × 31 días = 310 GiB al mes, por debajo del 1 TiB gratuito, **aunque
  se consumiera la cuota completa todos los días**. El proyecto real escanea unos pocos MB al
  día.
- **Cloud Run**: con una sola instancia de 1 vCPU, el peor caso (ocupada las 24 horas por un
  ataque) se acerca a los 2,6 millones de vCPU-segundos al mes. Eso **sí** superaría los
  180 000 gratuitos, y por eso existen las capas 5, 6 y 7. Con uso normal (unos pocos
  segundos al día) el consumo es menor al 1 %.
- **Gemini**: si la API key pertenece a un proyecto sin facturación, Google solo permite la capa
  gratuita. Al agotar el límite responde error 429; nunca cobra.
- **Cloud Storage**: los datos crudos pesan del orden de MB; el límite gratuito es de 5 GB en
  us-central1.

## Lo que este proyecto NO usa (y por qué)

| Servicio | Costo aproximado | Reemplazo |
|---|---|---|
| Cloud Composer | Cientos de USD/mes | Cloud Scheduler + Cloud Run Jobs |
| Vertex AI | Paga por uso desde el primer token | Gemini API vía AI Studio |
| Streaming inserts de BigQuery | Por GB insertado | Load jobs (gratis) |
| Cloud SQL | Se cobra por hora aunque no se use | BigQuery |
| Balanceadores de carga, Cloud NAT, conectores VPC | Por hora | URL nativa de Cloud Run |
| Dataflow, Dataproc | Por hora de cómputo | Python en Cloud Run Jobs |
| Región southamerica-west1 | Fuera de la capa gratuita de Storage | us-central1 |

## Checklist antes de cada `terraform apply`

- [ ] ¿El recurso nuevo aparece en la [capa gratuita](https://cloud.google.com/free)?
- [ ] ¿Está en `us-central1` o en la multirregión `US`?
- [ ] ¿Tiene límite de escala o de uso?
- [ ] ¿Las consultas nuevas filtran por partición y no usan `SELECT *`?
- [ ] ¿El job de Cloud Build o el despliegue no dejan imágenes huérfanas? (la política de
      limpieza del repositorio conserva solo las 2 más recientes)

## Orden de despliegue (fase 0)

Primero se aplica **solo** el blindaje; el resto de la infraestructura se crea después.

```powershell
cd infra/terraform
terraform init
terraform apply -target="google_project_service.apis" -target="google_billing_budget.presupuesto" -target="google_cloudfunctions2_function.corte_facturacion" -target="google_service_usage_consumer_quota_override.bq_bytes_diarios"
```

Después de verificarlo, el resto:

```powershell
terraform apply
```

## Probar el corte

Hazlo una vez en un **proyecto de prueba**, nunca en uno con datos que te importen. Este
mensaje simula que el gasto superó el presupuesto (las comillas van escapadas con `\` porque
Windows PowerShell 5.1 las elimina al pasarlas a programas externos):

```powershell
gcloud pubsub topics publish alertas-presupuesto --message='{\"costAmount\": 2.0, \"budgetAmount\": 1.0}'
```

Luego revisa en Facturación que el proyecto quedó **sin cuenta de facturación vinculada**, y
en los logs de la función el mensaje `Facturación desvinculada`.

## Qué pasa si se activa el corte

1. Los servicios pagados del proyecto se detienen (Cloud Run, BigQuery con facturación, etc.).
2. **No se pierde nada al instante**, pero si el proyecto queda mucho tiempo sin facturación,
   Google puede eliminar recursos. Revisa la causa pronto.
3. Para reactivarlo: corrige la causa y vuelve a vincular la cuenta de facturación en
   Facturación → Administrar proyectos.

## Limitaciones honestas

- Los datos de facturación llegan con **algunas horas de retraso**, por lo que el corte no es
  instantáneo. Las capas 1 a 5 existen para que nunca se llegue a necesitarlo.
- Los montos de la capa gratuita los define Google y pueden cambiar; revisa
  [cloud.google.com/free](https://cloud.google.com/free) cada cierto tiempo.
- La API key de Gemini en capa gratuita implica que Google puede usar los prompts para mejorar
  sus modelos. Aquí da igual: los datos son públicos.
