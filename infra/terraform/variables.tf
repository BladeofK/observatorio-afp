variable "proyecto_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "region" {
  description = "Región. us-central1 está dentro de la capa gratuita de Cloud Run y Storage."
  type        = string
  default     = "us-central1"

  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1"], var.region)
    error_message = "Usa us-central1, us-east1 o us-west1: son las regiones de la capa gratuita de Storage."
  }
}

variable "cuenta_facturacion" {
  description = "ID de la cuenta de facturación (formato 0X0X0X-0X0X0X-0X0X0X)."
  type        = string
}

variable "moneda" {
  description = "Moneda de la cuenta de facturación (USD o CLP). Debe coincidir con la cuenta."
  type        = string
  default     = "USD"
}

variable "monto_presupuesto" {
  description = "Tope mensual. Al alcanzarlo se desvincula la facturación (1 USD o ~1000 CLP)."
  type        = number
  default     = 1
}

variable "bq_cuota_diaria_mib" {
  description = "Máximo de MiB que BigQuery puede escanear por día en el proyecto. 10240 MiB = 10 GiB/día = ~310 GiB/mes, bajo el 1 TiB gratuito."
  type        = number
  default     = 10240

  validation {
    condition     = var.bq_cuota_diaria_mib <= 30000
    error_message = "Sobre ~30 000 MiB/día, un mes completo podría superar el 1 TiB gratuito."
  }
}

variable "repositorio_github" {
  description = "Repositorio autorizado a desplegar (formato propietario/nombre), p. ej. usuario/observatorio-afp."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.repositorio_github))
    error_message = "Usa el formato propietario/nombre."
  }
}

variable "imagen" {
  description = "Imagen Docker de la app. Mientras sea null no se crean Cloud Run ni Scheduler."
  type        = string
  default     = null
}

variable "modelo_gemini" {
  description = "Modelo de Gemini. Google retira versiones con el tiempo: si /preguntar responde 503 con código 404, cambia este valor por uno vigente (no requiere reconstruir la imagen)."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "modelos_gemini_respaldo" {
  description = "Modelos que se prueban en orden si el principal está saturado, sin cuota o lento."
  type        = list(string)
  default     = ["gemini-flash-lite-latest", "gemini-flash-latest"]
}

variable "usar_gemini" {
  description = "true solo después de cargar la API key de Gemini en Secret Manager."
  type        = bool
  default     = false
}
