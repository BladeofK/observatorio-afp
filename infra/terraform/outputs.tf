output "bucket_datos" {
  value = google_storage_bucket.datos.name
}

output "repositorio_imagenes" {
  description = "Prefijo para etiquetar la imagen antes del docker push."
  value       = "${var.region}-docker.pkg.dev/${var.proyecto_id}/${google_artifact_registry_repository.imagenes.repository_id}"
}

output "url_api" {
  value = local.desplegar ? google_cloud_run_v2_service.api[0].uri : "(se crea al definir var.imagen)"
}
