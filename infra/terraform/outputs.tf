output "artifact_registry_repository_name" {
  description = "Fully qualified Artifact Registry repository name."
  value       = google_artifact_registry_repository.devobs_images.name
}

output "artifact_registry_docker_endpoint" {
  description = "Docker endpoint for the repository; this does not grant push or pull permissions."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.devobs_images.repository_id}"
}
