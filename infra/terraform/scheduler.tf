# Dispara el job ETL todos los días a las 08:00 (hora de Chile).
# Capa gratuita: 3 jobs de Scheduler por cuenta de facturación; aquí se usa 1.

resource "google_cloud_run_v2_job_iam_member" "scheduler_ejecuta_etl" {
  count    = local.desplegar ? 1 : 0
  name     = google_cloud_run_v2_job.etl[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "etl_diario" {
  count            = local.desplegar ? 1 : 0
  name             = "observatorio-etl-diario"
  region           = var.region
  schedule         = "0 8 * * *"
  time_zone        = "America/Santiago"
  attempt_deadline = "320s"

  # Sin bloque retry_config a propósito: el valor por defecto de Scheduler ya es 0 reintentos
  # (un fallo se revisa, no se repite en bucle). Declararlo explícito causa un diff
  # permanente, porque la API no guarda el valor por defecto.

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.proyecto_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.etl[0].name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.scheduler_ejecuta_etl]
}
