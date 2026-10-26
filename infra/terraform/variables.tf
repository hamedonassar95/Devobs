variable "project_id" {
  description = "Google Cloud project ID that will own the Artifact Registry repository."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a 6–30 character Google Cloud project ID."
  }
}

variable "region" {
  description = "Google Cloud region for the container repository."
  type        = string
  default     = "us-central1"
}

variable "repository_id" {
  description = "Artifact Registry repository identifier."
  type        = string
  default     = "devobs-images"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,61}[a-z0-9]$", var.repository_id))
    error_message = "repository_id must be 5–63 lowercase letters, digits, or hyphens and start with a letter."
  }
}
