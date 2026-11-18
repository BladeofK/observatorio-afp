# Solo se crea el contenedor del secreto: el valor se carga a mano para que la API key
# nunca quede en el estado de Terraform ni en git.
#
# BLINDAJE · capa 4: la API key debe crearse en AI Studio dentro de un proyecto SIN
# facturación. Así Google solo permite la capa gratuita y responde 429 al agotarla.
#
# Cargar el valor (una vez, en PowerShell; -NoNewline evita guardar un salto de línea):
#   Set-Content -NoNewline -Path clave.txt -Value "TU_API_KEY"
#   gcloud secrets versions add gemini-api-key --data-file=clave.txt
#   Remove-Item clave.txt
# Luego: usar_gemini = true en terraform.tfvars.

resource "google_secret_manager_secret" "gemini" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
