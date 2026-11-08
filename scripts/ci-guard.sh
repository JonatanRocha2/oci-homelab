#!/usr/bin/env bash
# Recusa trace e debug antes de qualquer comando que leia segredo.
umask 077
if [[ -n "${ACTIONS_STEP_DEBUG:-}" || -n "${ACTIONS_RUNNER_DEBUG:-}" ]]; then
  printf 'debug do runner recusado\n' >&2
  exit 1
fi
case $- in
  *x*)
    printf 'trace recusado\n' >&2
    exit 1
    ;;
esac
if [[ "${GITHUB_REPOSITORY:-}" != "JonatanRocha2/oci-homelab" ]]; then
  printf 'repositorio recusado\n' >&2
  exit 1
fi
if [[ "${GITHUB_REF:-}" != "refs/heads/main" || "${GITHUB_EVENT_NAME:-}" != "workflow_dispatch" ]]; then
  printf 'somente workflow_dispatch em main\n' >&2
  exit 1
fi
if [[ -z "${RUNNER_TEMP:-}" ]]; then
  printf 'RUNNER_TEMP ausente\n' >&2
  exit 1
fi
