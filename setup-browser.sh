#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  ./setup.sh
fi

.venv/bin/python -m pip install -r requirements-browser.txt
export PLAYWRIGHT_BROWSERS_PATH="$PROJECT_DIR/.playwright"

if [[ -x .local-chromium/usr/lib/chromium/chromium ]]; then
  echo "Chromium local ya está disponible."
  exit 0
fi

echo "Instalando Chromium local para el agente web..."
if .venv/bin/python -m playwright install chromium; then
  echo "Browser agent instalado."
  exit 0
fi

echo "El CDN de Playwright no respondió; probando el paquete Debian sin instalarlo..." >&2
if command -v apt-get >/dev/null 2>&1 && command -v dpkg-deb >/dev/null 2>&1; then
  mkdir -p downloads .local-chromium
  DOWNLOAD_DIR="$(mktemp -d "$PROJECT_DIR/downloads/chromium.XXXXXX")"
  trap 'rm -rf -- "$DOWNLOAD_DIR"' EXIT
  (
    cd "$DOWNLOAD_DIR"
    apt-get download chromium chromium-common
    for package in ./*.deb; do
      dpkg-deb -x "$package" "$PROJECT_DIR/.local-chromium"
    done
  )
fi

if [[ ! -x .local-chromium/usr/lib/chromium/chromium ]]; then
  echo "Chromium no pudo instalarse. La aplicación principal seguirá funcionando." >&2
  exit 1
fi

echo "Browser agent instalado con Chromium local de Debian."

