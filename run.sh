#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "No existe .venv. Ejecuta primero ./setup.sh" >&2
  exit 1
fi

export ANKI_BUILDER_DATA_DIR="$PROJECT_DIR/data"
export ANKI_BUILDER_EXPORT_DIR="$PROJECT_DIR/exports"
export PLAYWRIGHT_BROWSERS_PATH="$PROJECT_DIR/.playwright"
export FLASK_DEBUG="${FLASK_DEBUG:-0}"

exec .venv/bin/python -m immersion_anki
