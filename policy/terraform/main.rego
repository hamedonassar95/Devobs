package main

import rego.v1

allowed_top_level_blocks := {"provider", "resource", "terraform", "variable", "output"}
allowed_repository_fields := {"description", "format", "labels", "location", "repository_id"}

resource_blocks(document) := object.get(object.get(object.get(document, "contents", {}), "resource", {}), "google_artifact_registry_repository", {})
repo_blocks(document) := object.get(resource_blocks(document), "devobs_images", [])
google_provider_blocks(document) := object.get(object.get(object.get(document, "contents", {}), "provider", {}), "google", [])

all_repo_blocks := [block |
  some document in input
  blocks := repo_blocks(document)
  some block in blocks
]

all_google_provider_blocks := [block |
  some document in input
  blocks := google_provider_blocks(document)
  some block in blocks
]

deny contains message if {
  some document in input
  contents := object.get(document, "contents", {})
  some block_type in object.keys(contents)
  not allowed_top_level_blocks[block_type]
  message := sprintf("top-level Terraform block is not allowlisted: %s", [block_type])
}

deny contains message if {
  some document in input
  resources := object.get(object.get(document, "contents", {}), "resource", {})
  some resource_type in object.keys(resources)
  resource_type != "google_artifact_registry_repository"
  message := sprintf("Terraform resource type is not allowlisted: %s", [resource_type])
}

deny contains "exactly one google_artifact_registry_repository.devobs_images block is required" if {
  count(all_repo_blocks) != 1
}

deny contains "only the devobs_images repository name is allowlisted" if {
  some document in input
  resources := object.get(object.get(document, "contents", {}), "resource", {})
  repositories := object.get(resources, "google_artifact_registry_repository", {})
  some name in object.keys(repositories)
  name != "devobs_images"
}

deny contains "repository format must be DOCKER" if {
  some repository in all_repo_blocks
  repository.format != "DOCKER"
}

deny contains "repository location must use var.region" if {
  some repository in all_repo_blocks
  repository.location != "${var.region}"
}

deny contains "repository id must use var.repository_id" if {
  some repository in all_repo_blocks
  repository.repository_id != "${var.repository_id}"
}

deny contains "repository fields include an unreviewed setting" if {
  some repository in all_repo_blocks
  some field in object.keys(repository)
  not allowed_repository_fields[field]
}

deny contains "required repository labels must be set" if {
  some repository in all_repo_blocks
  object.get(repository, "labels", {}).application != "devobs"
}

deny contains "required repository labels must be set" if {
  some repository in all_repo_blocks
  object.get(repository, "labels", {}).managed_by != "terraform"
}

deny contains "repository must use exactly the reviewed labels" if {
  some repository in all_repo_blocks
  object.keys(object.get(repository, "labels", {})) != {"application", "managed_by"}
}

deny contains message if {
  some document in input
  providers := object.get(object.get(document, "contents", {}), "provider", {})
  some provider_type in object.keys(providers)
  provider_type != "google"
  message := sprintf("Terraform provider is not allowlisted: %s", [provider_type])
}

deny contains "exactly one Google provider block is required" if {
  count(all_google_provider_blocks) != 1
}

deny contains "Google provider must use project_id and region variables only" if {
  some provider in all_google_provider_blocks
  some field in object.keys(provider)
  field != "project"
  field != "region"
}

deny contains "Google provider project must use var.project_id" if {
  some provider in all_google_provider_blocks
  provider.project != "${var.project_id}"
}

deny contains "Google provider region must use var.region" if {
  some provider in all_google_provider_blocks
  provider.region != "${var.region}"
}
