#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "${root}/scripts/pipeline_checks.py" selftest
python3 "${root}/scripts/pipeline_checks.py" workflows --root "${root}"
