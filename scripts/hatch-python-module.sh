#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <module> [args...]" >&2
  exit 2
fi

module=$1
shift || true

env_name=${HATCH_ENV:-default}

resolve_env_path() {
  hatch env find "$env_name" | tail -n 1 | tr -d '\r'
}

env_path=$(resolve_env_path)

if [ ! -x "${env_path}/bin/python" ]; then
  hatch env create "$env_name" >/dev/null
  env_path=$(resolve_env_path)
fi

"${env_path}/bin/python" -m "$module" "$@"
