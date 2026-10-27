# Creates grow8-backend\.venv for the EDITOR ONLY (VS Code / Pylance / ruff), from the
# same pinned requirement files the Docker images use. The code still RUNS in Docker
# (`make up`, `make test`); do not run the API or tests from this venv.
#
# Usage (PowerShell, from grow8-backend):  .\scripts\setup-venv.ps1
# If scripts are blocked: powershell -ExecutionPolicy Bypass -File .\scripts\setup-venv.ps1
# Re-run after any requirements*.txt or shared\pyproject.toml change.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv")) {
    $created = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv .venv
        $created = $LASTEXITCODE -eq 0
    }
    if (-not $created) {
        & python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))"
        if ($LASTEXITCODE -ne 0) { throw "Python 3.12 not found (the images use 3.12). Install it first." }
        & python -m venv .venv
    }
}

$venvPython = ".venv\Scripts\python.exe"
& $venvPython -m pip install --quiet --disable-pip-version-check --upgrade pip
# shared\ is installed editable in setuptools' "compat" mode (a plain path in a .pth file).
# The default mode uses an import hook that Pylance cannot follow (unresolved grow8_common).
& $venvPython -m pip install --quiet --disable-pip-version-check `
    --config-settings editable_mode=compat `
    -e shared `
    -r api/requirements-dev.txt `
    -r services/creator_service/requirements-dev.txt `
    -r services/contributor_service/requirements-dev.txt `
    -r services/admin_service/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "Editor venv ready: $venvPython"
Write-Host "Open grow8.code-workspace (repository root) in VS Code (File > Open Workspace from File)."
