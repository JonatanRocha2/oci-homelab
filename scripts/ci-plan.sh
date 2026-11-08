#!/usr/bin/env bash
# Gera um plano e o publica so cifrado. Nao aplica.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=ci-guard.sh
source "${root}/scripts/ci-guard.sh"
cd "${root}"

: "${HOMELAB_TFVARS:?}"
: "${HOMELAB_BACKEND_CONFIG:?}"
: "${HOMELAB_PLAN_PASSPHRASE:?}"
: "${OCI_CUSTOMER_SECRET_KEY_ID:?}"
: "${OCI_CUSTOMER_SECRET_KEY:?}"
: "${GITHUB_SHA:?}"

if [[ ! "${GITHUB_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'sha recusado\n' >&2
  exit 1
fi
if [[ "$(git rev-parse HEAD)" != "${GITHUB_SHA}" ]]; then
  printf 'checkout diferente do sha\n' >&2
  exit 1
fi
if [[ "${ALLOW_EMPTY_STATE:-false}" != "true" && "${ALLOW_EMPTY_STATE:-false}" != "false" ]]; then
  printf 'acknowledge_empty_state recusado\n' >&2
  exit 1
fi

work="$(mktemp -d "${RUNNER_TEMP}/plan.XXXXXX")"
chmod 700 "${work}"
trap 'rm -rf "${work}"' EXIT

python3 "${root}/scripts/write_secret_file.py" tfvars HOMELAB_TFVARS "${work}/terraform.tfvars"
python3 "${root}/scripts/write_secret_file.py" backend HOMELAB_BACKEND_CONFIG "${work}/backend.hcl"

session="$(python3 "${root}/scripts/oci_api_session.py")"
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

if ! tofu -chdir=infra init -input=false -no-color -lock-timeout=5m -backend-config="${work}/backend.hcl" >"${work}/init.log" 2>&1; then
  redact_fail "${work}/init.log"
fi
if ! tofu -chdir=infra state pull -no-color >"${work}/state.json" 2>"${work}/state.err"; then
  redact_fail "${work}/state.err"
fi
python3 "${root}/scripts/pipeline_checks.py" guard-state --state "${work}/state.json"
if ! tofu -chdir=infra plan -input=false -no-color -lock-timeout=5m -out="${work}/homelab.tfplan" -var-file="${work}/terraform.tfvars" >"${work}/plan.log" 2>&1; then
  redact_fail "${work}/plan.log"
fi
if ! tofu -chdir=infra show -json -no-color "${work}/homelab.tfplan" >"${work}/plan.json" 2>"${work}/show.err"; then
  redact_fail "${work}/show.err"
fi
python3 "${root}/scripts/pipeline_checks.py" write-metadata \
  --plan-json "${work}/plan.json" \
  --plan-bin "${work}/homelab.tfplan" \
  --state "${work}/state.json" \
  --sha "${GITHUB_SHA}" \
  --out "${work}/metadata.json"
python3 "${root}/scripts/pipeline_checks.py" summarize --plan-json "${work}/plan.json" >"${work}/summary.txt"
install -m 600 /dev/null "${RUNNER_TEMP}/homelab-plan.enc"
tar -C "${work}" -cf - homelab.tfplan metadata.json \
  | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:HOMELAB_PLAN_PASSPHRASE -out "${RUNNER_TEMP}/homelab-plan.enc"
chmod 600 "${RUNNER_TEMP}/homelab-plan.enc"
tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}" <"${work}/summary.txt"
printf 'plan ok\n'
