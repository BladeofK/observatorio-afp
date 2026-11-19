output "bucket_datos" {
  value = google_storage_bucket.datos.name
}

output "repositorio_imagenes" {
  description = "Prefijo para etiquetar la imagen antes del docker push."
  value       = "${var.region}-docker.pkg.dev/${var.proyecto_id}/${google_artifact_registry_repository.imagenes.repository_id}"
}

output "github_wif_provider" {
  description = "Valor para la variable GCP_WIF_PROVIDER del repositorio en GitHub."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deploy_sa" {
  description = "Valor para la variable GCP_DEPLOY_SA del repositorio en GitHub."
  value       = google_service_account.github_deploy.email
}

output "url_api" {
  value = local.desplegar ? google_cloud_run_v2_service.api[0].uri : "(se crea al definir var.imagen)"
}
