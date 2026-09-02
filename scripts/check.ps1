$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Set-Location (Join-Path $ProjectRoot 'backend')
& '.\.venv\Scripts\python.exe' -m ruff check app tests
& '.\.venv\Scripts\python.exe' -m ruff format --check app tests
& '.\.venv\Scripts\python.exe' -m pytest

Set-Location (Join-Path $ProjectRoot 'frontend')
npm run lint
npm run build

Write-Host 'All checks passed.'
