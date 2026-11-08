#!/usr/bin/env bash
# Aplica somente o plano cifrado ja conferido. Nao gera outro plano.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=ci-guard.sh
source "${root}/scripts/ci-guard.sh"
cd "${root}"

: "${HOMELAB_BACKEND_CONFIG:?}"
: "${HOMELAB_PLAN_PASSPHRASE:?}"
: "${OCI_CUSTOMER_SECRET_KEY_ID:?}"
: "${OCI_CUSTOMER_SECRET_KEY:?}"
: "${GIT_SHA:?}"
: "${GITHUB_ACTOR:?}"
: "${APPROVALS_FILE:?}"
: "${PLAN_RUN_FILE:?}"
: "${PLAN_BUNDLE:?}"

if [[ ! "${GIT_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'sha recusado\n' >&2
  exit 1
fi
if [[ "$(git rev-parse HEAD)" != "${GIT_SHA}" ]]; then
  printf 'checkout diferente do sha do plano\n' >&2
  exit 1
fi
if [[ "${ALLOW_EMPTY_STATE:-false}" != "true" && "${ALLOW_EMPTY_STATE:-false}" != "false" ]]; then
  printf 'acknowledge_empty_state recusado\n' >&2
  exit 1
fi

python3 "${root}/scripts/pipeline_checks.py" require-approval --file "${APPROVALS_FILE}" --actor "${GITHUB_ACTOR}"
python3 "${root}/scripts/pipeline_checks.py" verify-run --run "${PLAN_RUN_FILE}" --sha "${GIT_SHA}"

work="$(mktemp -d "${RUNNER_TEMP}/apply.XXXXXX")"
chmod 700 "${work}"
trap 'rm -rf "${work}"' EXIT

if ! openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:HOMELAB_PLAN_PASSPHRASE -in "${PLAN_BUNDLE}" -out "${work}/bundle.tar" 2>"${work}/decrypt.err"; then
  printf 'decifra falhou\n' >&2
  exit 1
fi
got="$(tar -tf "${work}/bundle.tar" | LC_ALL=C sort | tr '\n' ' ')"
if [[ "${got}" != "homelab.tfplan metadata.json " ]]; then
  printf 'pacote do plano recusado\n' >&2
  exit 1
fi
tar -C "${work}" -xf "${work}/bundle.tar"

python3 "${root}/scripts/pipeline_checks.py" verify-binding \
  --metadata "${work}/metadata.json" \
  --plan-bin "${work}/homelab.tfplan" \
  --sha "${GIT_SHA}"

session="$(python3 "${root}/scripts/oci_rpst_session.py")"
# shellcheck disable=SC1090
source "${session}"
export AWS_ACCESS_KEY_ID="${OCI_CUSTOMER_SECRET_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${OCI_CUSTOMER_SECRET_KEY}"
export TF_IN_AUTOMATION=1
export TF_INPUT=0
unset TF_LOG TF_LOG_PATH TF_DATA_DIR || true

redact_fail() {
  python3 "${root}/scripts/pipeline_checks.py" redact --file "$1" >&2 || true
  exit 1
}

python3 "${root}/scripts/write_secret_file.py" backend HOMELAB_BACKEND_CONFIG "${work}/backend.hcl"
if ! tofu -chdir=infra init -input=false -no-color -lock-timeout=5m -backend-config="${work}/backend.hcl" >"${work}/init.log" 2>&1; then
  redact_fail "${work}/init.log"
fi
if ! tofu -chdir=infra state pull -no-color >"${work}/state.json" 2>"${work}/state.err"; then
  redact_fail "${work}/state.err"
fi
python3 "${root}/scripts/pipeline_checks.py" guard-apply-state \
  --state "${work}/state.json" \
  --metadata "${work}/metadata.json"

if ! tofu -chdir=infra apply -auto-approve -input=false -no-color -lock-timeout=5m "${work}/homelab.tfplan" >"${work}/apply.log" 2>&1; then
  redact_fail "${work}/apply.log"
fi
printf 'apply ok\n'
