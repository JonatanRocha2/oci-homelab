# No computador do operador a autenticacao continua a chave de API do
# arquivo de configuracao, fora deste repositorio. O workflow de plano
# e apply define OCI_AUTH=ResourcePrincipal depois de trocar um JWT
# efemero do GitHub por um RPST. Este bloco nao recebe chave,
# fingerprint, usuario nem tenancy.
provider "oci" {
  region              = var.region
  config_file_profile = var.oci_config_profile
}
