# Terraform stub, will be useful if we branch out to many counties

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {}
variable "region" {
  default = "us-central1"
}

# Example bucket creation
resource "google_storage_bucket" "raw_cases" {
  name     = "${var.project_id}-foreclosure-raw"
  location = var.region
  uniform_bucket_level_access = true
}

# TODO: add Cloud Run Job resources, IAM bindings, and Workflows definitions.
