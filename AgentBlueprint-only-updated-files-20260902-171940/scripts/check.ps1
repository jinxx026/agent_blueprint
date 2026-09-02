$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Push-Location (Join-Path $ProjectRoot 'backend')
try {
    & '.\.venv\Scripts\python.exe' -m ruff check app tests ..\frontend
    if ($LASTEXITCODE -ne 0) { throw 'Ruff lint check failed.' }
    & '.\.venv\Scripts\python.exe' -m ruff format --check app tests ..\frontend
    if ($LASTEXITCODE -ne 0) { throw 'Ruff format check failed.' }
    & '.\.venv\Scripts\python.exe' -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Pytest failed.' }
}
finally {
    Pop-Location
}

Write-Host 'All checks passed.'
