terraform {
  required_version = "~> 1.17.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 8.8.1"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "devobs_images" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Container images for the Devobs static website."
  format        = "DOCKER"

  labels = {
    application = "devobs"
    managed_by  = "terraform"
  }
}
