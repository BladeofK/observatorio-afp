terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Estado local (archivo terraform.tfstate, excluido de git).
  # Mejora opcional: backend "gcs" en un bucket del propio proyecto.
}

# user_project_override + billing_project: necesarios para la API de presupuestos
# cuando se usan credenciales de usuario (gcloud auth application-default login).
provider "google" {
  project               = var.proyecto_id
  region                = var.region
  user_project_override = true
  billing_project       = var.proyecto_id
}

provider "google-beta" {
  project               = var.proyecto_id
  region                = var.region
  user_project_override = true
  billing_project       = var.proyecto_id
}

data "google_project" "este" {
  project_id = var.proyecto_id
}
