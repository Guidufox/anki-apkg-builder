$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error "No existe .venv. Ejecuta primero setup.bat o .\setup.ps1"
}

$env:ANKI_BUILDER_DATA_DIR = Join-Path $PSScriptRoot "data"
$env:ANKI_BUILDER_EXPORT_DIR = Join-Path $PSScriptRoot "exports"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot ".playwright"
$env:FLASK_DEBUG = "0"

& $PythonExe -m immersion_anki

