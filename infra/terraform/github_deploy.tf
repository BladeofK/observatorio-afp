# Despliegue automático desde GitHub Actions con Workload Identity Federation:
# GitHub presenta un token OIDC firmado y GCP lo cambia por credenciales temporales.
# No existe ninguna llave JSON que se pueda filtrar.
#
# Solo el repositorio indicado, y solo desde la rama main, puede usar esta identidad.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Cualquier otro repositorio o rama recibe un rechazo antes de obtener credenciales.
  attribute_condition = "assertion.repository == '${var.repositorio_github}' && assertion.ref == 'refs/heads/main'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github_deploy" {
  account_id   = "github-deploy"
  display_name = "Despliegue desde GitHub Actions"
}

resource "google_service_account_iam_member" "github_impersona_deploy" {
  service_account_id = google_service_account.github_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.repositorio_github}"
}

# Permisos mínimos para desplegar: subir imágenes y actualizar la API y el job.
resource "google_artifact_registry_repository_iam_member" "github_sube_imagenes" {
  location   = google_artifact_registry_repository.imagenes.location
  repository = google_artifact_registry_repository.imagenes.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_deploy.email}"
}

resource "google_project_iam_member" "github_despliega_cloud_run" {
  project = var.proyecto_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_deploy.email}"
}

# Para desplegar una revisión que corre como la cuenta de la API o del ETL, hay que poder
# "actuar como" esas cuentas (y solo esas).
resource "google_service_account_iam_member" "github_actua_como" {
  for_each = {
    api = google_service_account.api.name
    etl = google_service_account.etl.name
  }
  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deploy.email}"
}
