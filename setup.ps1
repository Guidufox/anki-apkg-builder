$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv .venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
} else {
    Write-Error "Python 3 no está instalado o no está en PATH. Instálalo desde python.org."
}

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force -Path data, exports | Out-Null

Write-Host ""
Write-Host "Instalación terminada. Ejecuta run.bat o .\run.ps1" -ForegroundColor Green
Write-Host "El browser agent es opcional. Para instalarlo: .\setup-browser.ps1"

