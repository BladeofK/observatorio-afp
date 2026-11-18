# API (Cloud Run Service) y ETL (Cloud Run Job). Se crean cuando var.imagen tiene valor.
#
# BLINDAJE · capa 3: escala a cero, máximo 1 instancia, CPU solo durante las requests.
# Aun bajo ataque, el costo queda acotado a una instancia (y lo frenan las capas 5 a 7).

locals {
  desplegar = var.imagen != null

  entorno_comun = {
    GCP_PROJECT = var.proyecto_id
    BQ_LOCATION = "US"
    BUCKET      = google_storage_bucket.datos.name
  }
}

resource "google_cloud_run_v2_service" "api" {
  count               = local.desplegar ? 1 : 0
  name                = "observatorio-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.api.email
    max_instance_request_concurrency = 20
    timeout                          = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.imagen

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true # CPU facturada solo mientras atiende requests
        startup_cpu_boost = false
      }

      dynamic "env" {
        for_each = local.entorno_comun
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.usar_gemini ? [1] : []
        content {
          name = "GEMINI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gemini.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis, google_secret_manager_secret_iam_member.api_gemini]
}

# API pública (solo lectura). El límite de solicitudes está en la app.
resource "google_cloud_run_v2_service_iam_member" "api_publica" {
  count    = local.desplegar ? 1 : 0
  name     = google_cloud_run_v2_service.api[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "etl" {
  count               = local.desplegar ? 1 : 0
  name                = "observatorio-etl"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1

    template {
      service_account = google_service_account.etl.email
      max_retries     = 1
      timeout         = "900s"

      containers {
        image   = var.imagen
        command = ["python", "-m", "observatorio.etl.main"]
        args    = ["diario"]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        dynamic "env" {
          for_each = local.entorno_comun
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}
