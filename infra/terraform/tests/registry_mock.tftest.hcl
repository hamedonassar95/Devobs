# P01 T09: provider-mocked, plan-only acceptance tests.
# Every run is plan-only: never apply or contact Google Cloud.
# Docs: https://developer.hashicorp.com/terraform/language/tests/mocking
#       https://developer.hashicorp.com/terraform/language/tests

mock_provider "google" {}

variables {
  project_id    = "devobs-ci-synthetic"
  region        = "us-central1"
  repository_id = "devobs-images"
}

run "docker_repository_configuration" {
  command = plan

  assert {
    condition     = google_artifact_registry_repository.devobs_images.format == "DOCKER"
    error_message = "Artifact Registry repository must use Docker format."
  }

  assert {
    condition     = google_artifact_registry_repository.devobs_images.location == "us-central1"
    error_message = "Artifact Registry repository location unexpectedly changed."
  }

  assert {
    condition     = google_artifact_registry_repository.devobs_images.repository_id == "devobs-images"
    error_message = "Artifact Registry repository ID unexpectedly changed."
  }

  assert {
    condition     = output.artifact_registry_docker_endpoint == "us-central1-docker.pkg.dev/devobs-ci-synthetic/devobs-images"
    error_message = "Artifact Registry endpoint changed for the synthetic inputs."
  }
}

run "reject_invalid_project_id" {
  command = plan

  variables {
    project_id = "INVALID_PROJECT"
  }

  expect_failures = [var.project_id]
}

run "reject_invalid_repository_id" {
  command = plan

  variables {
    repository_id = "INVALID_REPOSITORY"
  }

  expect_failures = [var.repository_id]
}
