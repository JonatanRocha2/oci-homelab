#!/usr/bin/env bash
# Validacao local e de CI. Nao inicializa backend, nao planeja na OCI e nao aplica.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${root}"

unset OCI_CLI_AUTH OCI_CLI_CONFIG_FILE OCI_CLI_KEY_FILE OCI_CLI_USER OCI_CLI_TENANCY OCI_CLI_FINGERPRINT || true

"${root}/scripts/check-repository.sh"

tofu -chdir=infra fmt -check -recursive
tofu -chdir=infra init -backend=false -input=false -no-color
tofu -chdir=infra validate -no-color
tofu -chdir=infra test -no-color

(
  cd ansible
  ansible-lint
  ansible-playbook --syntax-check -i inventories/example/hosts.yml site.yml
)

printf 'ci: ok\n'
