# Data lake (bronze crudo). us-central1: dentro de los 5 GB gratuitos de Storage.

resource "google_storage_bucket" "datos" {
  name                        = "${var.proyecto_id}-datos"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # El "soft delete" guarda copias de lo borrado y ese espacio se cobra. Desactivado.
  soft_delete_policy {
    retention_duration_seconds = 0
  }

  depends_on = [google_project_service.apis]
}
