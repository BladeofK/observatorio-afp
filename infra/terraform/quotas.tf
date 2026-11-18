# BLINDAJE · capa 1: límite DURO de bytes escaneados por día en BigQuery.
# Al superarlo, BigQuery rechaza las consultas hasta el día siguiente: no hay cobro posible.
#
# El valor se expresa en MiB. Tras aplicar, confírmalo en la consola:
# IAM y administración → Cuotas → filtrar "BigQuery API" → "Query usage per day".
# Si el recurso fallara, se puede fijar el mismo límite a mano desde esa pantalla.

resource "google_service_usage_consumer_quota_override" "bq_bytes_diarios" {
  provider       = google-beta
  project        = var.proyecto_id
  service        = "bigquery.googleapis.com"
  metric         = urlencode("bigquery.googleapis.com/quota/query/usage")
  limit          = urlencode("/d/project")
  override_value = tostring(var.bq_cuota_diaria_mib)
  force          = true # Necesario porque se reduce la cuota (por defecto es ilimitada)

  depends_on = [google_project_service.apis]
}
