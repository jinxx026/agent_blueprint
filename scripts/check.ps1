$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Set-Location (Join-Path $ProjectRoot 'backend')
& '.\.venv\Scripts\python.exe' -m ruff check app tests ..\frontend
& '.\.venv\Scripts\python.exe' -m ruff format --check app tests ..\frontend
& '.\.venv\Scripts\python.exe' -m pytest

Set-Location $ProjectRoot
Write-Host 'All checks passed.'
