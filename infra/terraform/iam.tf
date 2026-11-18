# Cuentas de servicio con permisos mínimos (una por componente).

resource "google_service_account" "etl" {
  account_id   = "observatorio-etl"
  display_name = "Job ETL del observatorio"
}

resource "google_service_account" "api" {
  account_id   = "observatorio-api"
  display_name = "API del observatorio"
}

resource "google_service_account" "scheduler" {
  account_id   = "observatorio-scheduler"
  display_name = "Disparador diario del ETL"
}

# Ambas necesitan crear jobs de consulta (el costo se controla con la cuota y el tope).
resource "google_project_iam_member" "job_user" {
  for_each = {
    etl = google_service_account.etl.email
    api = google_service_account.api.email
  }
  project = var.proyecto_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${each.value}"
}

# ETL: escribe en las tres capas.
resource "google_bigquery_dataset_iam_member" "etl_editor" {
  for_each   = google_bigquery_dataset.capas
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.etl.email}"
}

resource "google_storage_bucket_iam_member" "etl_bucket" {
  bucket = google_storage_bucket.datos.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.etl.email}"
}

# API: SOLO lectura y SOLO de gold. Es la última barrera si el LLM generara SQL malicioso.
resource "google_bigquery_dataset_iam_member" "api_lector_gold" {
  dataset_id = google_bigquery_dataset.capas["gold"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "api_gemini" {
  secret_id = google_secret_manager_secret.gemini.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
