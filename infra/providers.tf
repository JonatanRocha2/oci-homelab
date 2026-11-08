# A autenticacao vem do arquivo de configuracao da OCI no computador
# do operador, fora deste repositorio. Este bloco nao recebe chave,
# fingerprint, usuario nem tenancy.
provider "oci" {
  region              = var.region
  config_file_profile = var.oci_config_profile
}
