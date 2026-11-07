terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "9.12.1"
    }
  }

  # Estado local de proposito. Nao ha backend remoto neste fundamento.
  backend "local" {
    path = "terraform.tfstate"
  }
}
