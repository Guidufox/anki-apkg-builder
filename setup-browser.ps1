$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    & (Join-Path $PSScriptRoot "setup.ps1")
}

& $PythonExe -m pip install -r requirements-browser.txt
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot ".playwright"
& $PythonExe -m playwright install chromium

Write-Host "Browser agent instalado localmente." -ForegroundColor Green

