#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SMOKE_SCRIPT="${REPO_ROOT}/scripts/devobs_intelligence/staging_smoke.py"

if [[ ! -f "${SMOKE_SCRIPT}" ]]; then
  printf '%s\n' "DevObs staging health check: BLOCKED (smoke script missing)" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "DevObs staging health check: BLOCKED (python3 unavailable)" >&2
  exit 127
fi

# Delegate all HTTPS, tenant-isolation, response-size and credential checks to
# the existing read-only smoke implementation. Never print supplied secrets.
exec python3 "${SMOKE_SCRIPT}"
