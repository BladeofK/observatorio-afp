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

  # Estado remoto en GCS: no depende del disco local y queda versionado (5 versiones
  # anteriores). El bucket se crea a mano una sola vez, antes del primer init, porque
  # Terraform no puede guardar su estado en un bucket que él mismo aún no creó:
  #   gcloud.cmd storage buckets create gs://<proyecto>-tfstate --location us-central1 \
  #     --uniform-bucket-level-access --public-access-prevention --soft-delete-duration 0
  #   gcloud.cmd storage buckets update gs://<proyecto>-tfstate --versioning
  backend "gcs" {
    bucket = "observatorio-afp-tfstate"
    prefix = "terraform/estado"
  }
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
