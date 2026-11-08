#!/usr/bin/env bash
# Confere o repositorio sem credencial e sem falar com a OCI.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${root}"

fail() {
  printf 'check-repository: %s\n' "$*" >&2
  exit 1
}

if git ls-files | grep -E -i '(^|/)\.env($|\.)|(^|/)terraform\.tfstate($|\.)|\.tfplan($|\.)|\.pem$|\.tfvars$|kubeconfig|(^|/)k3s\.yaml$|(^|/)id_rsa($|\.)|(^|/)id_ed25519($|\.)|\.key$'; then
  fail "arquivo de estado, plano, tfvars privado, kubeconfig ou chave esta versionado"
fi

# infra/tests cita um cabecalho de chave privada de proposito, para provar
# que a validacao o recusa. O restante do repositorio nao pode cita-lo.
if git grep -I -n -E 'BEGIN (OPENSSH |RSA |EC |PRIVATE )?PRIVATE KEY' -- . ':(exclude)infra/tests' >/dev/null; then
  fail "ha material de chave privada versionado"
fi

python3 "${root}/scripts/pipeline_checks.py" workflows --root "${root}"

if grep -R -n -E 'resource "oci_core_nat_gateway"|resource "oci_core_public_ip"|resource "oci_load_balancer"|resource "oci_network_load_balancer"|resource "oci_core_volume"|resource "oci_core_volume_backup"' infra --include='*.tf'; then
  fail "ha NAT, IP reservado, balanceador, volume extra ou backup"
fi

grep -q 'k3s_enabled: false' ansible/group_vars/all.yml || fail "k3s precisa nascer desligado"
grep -q 'k3s_version: "v1.37.2+k3s1"' ansible/roles/k3s/defaults/main.yml || fail "a versao do k3s nao esta fixada"
grep -q 'k3s_sha256_arm64: "a779ccf1e5e2e33a62f5a29c2f1c0bbf99431e100579d4c10f0aa0742a6aa84b"' ansible/roles/k3s/defaults/main.yml || fail "o checksum do binario k3s mudou sem revisao"
grep -q 'k3s_install_sha256: "ed01f89fd977bf20ac1516bbebf8370bf3ddbaa55dac8aba610956a4c78cc00b"' ansible/roles/k3s/defaults/main.yml || fail "o checksum do instalador k3s mudou sem revisao"
grep -q 'INSTALL_K3S_SKIP_DOWNLOAD: "true"' ansible/roles/k3s/tasks/main.yml || fail "o instalador do k3s precisa usar o binario ja verificado"
if grep -R -n -E 'fetch:|ansible\.builtin\.fetch' ansible/roles/k3s; then
  fail "o papel k3s nao pode copiar kubeconfig para fora do servidor"
fi

test -f infra/.terraform.lock.hcl || fail "falta o lockfile do provider"
grep -q 'oracle/oci' infra/.terraform.lock.hcl || fail "o lockfile nao fixa oracle/oci"

printf 'check-repository: ok\n'
