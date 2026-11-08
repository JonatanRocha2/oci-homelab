terraform {
  required_version = ">= 1.13.0, < 2.0.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "9.12.1"
    }
  }

  # O bucket, a regiao e o endpoint ficam fora do repositorio, em
  # -backend-config. Sem isso o init do plano remoto para. Nao ha
  # fallback para estado local vazio.
  # use_lockfile pede o write condicional If-None-Match do backend S3.
  # Um teste concorrente neste bucket, depois apagado, viu 412 enquanto
  # o objeto existia e 200 depois da remocao. O flag permanece ligado.
  backend "s3" {
    key                         = "oci-homelab/terraform.tfstate"
    use_lockfile                = true
    use_path_style              = true
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
  }
}
