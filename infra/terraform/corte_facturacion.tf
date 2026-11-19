# BLINDAJE · capa 7: cuando el gasto del mes alcanza el presupuesto, una Cloud Function
# desvincula la cuenta de facturación del proyecto y los servicios pagados se detienen.
# Patrón documentado por Google: "Disable billing usage with notifications".

resource "google_service_account" "corte_facturacion" {
  account_id   = "corte-facturacion"
  display_name = "Corte automático de facturación"
}

# Permite desvincular la facturación del proyecto. Si en la prueba aparece un error 403,
# agrega además a esta cuenta como "Billing Account Administrator" en la cuenta de
# facturación, como indica la guía de Google.
resource "google_project_iam_member" "corte_billing_manager" {
  project = var.proyecto_id
  role    = "roles/billing.projectManager"
  member  = "serviceAccount:${google_service_account.corte_facturacion.email}"
}

# El disparador de Eventarc invoca la función con esta misma cuenta.
resource "google_project_iam_member" "corte_invoker" {
  project = var.proyecto_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.corte_facturacion.email}"
}

# Eventarc exige que la cuenta del disparador pueda recibir eventos.
resource "google_project_iam_member" "corte_event_receiver" {
  project = var.proyecto_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.corte_facturacion.email}"
}

resource "google_storage_bucket" "fuentes_funciones" {
  name                        = "${var.proyecto_id}-fuentes-funciones"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 0
  }

  depends_on = [google_project_service.apis]
}

data "archive_file" "corte_facturacion" {
  type        = "zip"
  source_dir  = "${path.module}/funciones/corte_facturacion"
  output_path = "${path.module}/.build/corte_facturacion.zip"
}

resource "google_storage_bucket_object" "corte_facturacion" {
  # El hash en el nombre fuerza el redespliegue cuando cambia el código.
  name   = "corte_facturacion_${data.archive_file.corte_facturacion.output_md5}.zip"
  bucket = google_storage_bucket.fuentes_funciones.name
  source = data.archive_file.corte_facturacion.output_path
}

resource "google_cloudfunctions2_function" "corte_facturacion" {
  name     = "corte-facturacion"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "cortar_facturacion"
    source {
      storage_source {
        bucket = google_storage_bucket.fuentes_funciones.name
        object = google_storage_bucket_object.corte_facturacion.name
      }
    }
  }

  service_config {
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.corte_facturacion.email
    environment_variables = {
      PROYECTO_ID = var.proyecto_id
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.alertas_presupuesto.id
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.corte_facturacion.email
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.corte_billing_manager,
    google_project_iam_member.corte_invoker,
    google_project_iam_member.corte_event_receiver,
  ]
}
