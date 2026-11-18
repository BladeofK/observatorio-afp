# Un dataset por capa del modelo Medallón. Las tablas se crean con sql/ddl (comando setup).
# Multirregión US: compatible con el bucket en us-central1 para cargas desde GCS.

locals {
  capas = {
    bronze = "Datos crudos tal como llegan de las fuentes (todo STRING)"
    silver = "Datos tipados, normalizados y deduplicados"
    gold   = "Tablas analíticas listas para la API y el LLM"
  }
}

resource "google_bigquery_dataset" "capas" {
  for_each    = local.capas
  dataset_id  = each.key
  location    = "US"
  description = each.value

  delete_contents_on_destroy = false

  depends_on = [google_project_service.apis]
}
