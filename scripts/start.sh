#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo "Crie o ambiente e instale as dependências conforme o README."
  exit 1
fi
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$PWD/.browsers}"
exec .venv/bin/python -m uvicorn app.api:app --host "${OBSERVA_HOST:-127.0.0.1}" --port "${OBSERVA_PORT:-8000}"
