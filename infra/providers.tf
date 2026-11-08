# No computador do operador a autenticacao continua a chave de API do
# arquivo de configuracao, fora deste repositorio. No workflow, as
# variaveis de ambiente documentadas pelo provider (OCI_AUTH=APIKey e
# os campos da chave) tem precedencia sobre esse perfil. A chave que
# ja assina a CLI nao entra no workflow. Este bloco nao recebe chave,
# fingerprint, usuario nem tenancy.
provider "oci" {
  region              = var.region
  config_file_profile = var.oci_config_profile
}
