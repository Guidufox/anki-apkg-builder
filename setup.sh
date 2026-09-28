#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 no está instalado." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
mkdir -p data exports

export PLAYWRIGHT_BROWSERS_PATH="$PROJECT_DIR/.playwright"
if [[ "${SKIP_BROWSER_INSTALL:-0}" != "1" ]]; then
  echo "Instalando Chromium local para el agente web..."
  if ! .venv/bin/python -m playwright install chromium; then
    echo "El CDN de Playwright no respondió; probando el paquete Debian sin instalarlo..." >&2
    if command -v apt-get >/dev/null 2>&1 && command -v dpkg-deb >/dev/null 2>&1; then
      mkdir -p downloads .local-chromium
      DOWNLOAD_DIR="$(mktemp -d "$PROJECT_DIR/downloads/chromium.XXXXXX")"
      (
        cd "$DOWNLOAD_DIR"
        apt-get download chromium chromium-common
        for package in ./*.deb; do
          dpkg-deb -x "$package" "$PROJECT_DIR/.local-chromium"
        done
      ) || true
      rm -rf -- "$DOWNLOAD_DIR"
    fi
    if [[ ! -x .local-chromium/usr/lib/chromium/chromium ]]; then
      echo "Aviso: Chromium no pudo instalarse. La aplicación Anki seguirá funcionando." >&2
      echo "Reintenta luego con: PLAYWRIGHT_BROWSERS_PATH=\"$PROJECT_DIR/.playwright\" .venv/bin/python -m playwright install chromium" >&2
    fi
  fi
fi

echo
echo "Instalación terminada. Ejecuta: ./run.sh"
