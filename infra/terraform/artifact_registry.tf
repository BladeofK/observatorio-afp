# Repositorio de imágenes. Capa gratuita: 0,5 GB. La política de limpieza conserva
# solo las 2 versiones más recientes para no superarla nunca.

resource "google_artifact_registry_repository" "imagenes" {
  location      = var.region
  repository_id = "observatorio"
  format        = "DOCKER"
  description   = "Imagen única de la API y del job ETL"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "conservar-recientes"
    action = "KEEP"
    most_recent_versions {
      keep_count = 2
    }
  }

  cleanup_policies {
    id     = "borrar-el-resto"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.apis]
}
