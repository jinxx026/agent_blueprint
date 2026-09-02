$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Set-Location (Join-Path $ProjectRoot 'backend')
if (-not (Test-Path '.venv')) {
    py -3 -m venv .venv
}
& '.\.venv\Scripts\python.exe' -m pip install -e '.[dev,ui]'
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}

Set-Location $ProjectRoot
Write-Host 'Setup complete. Run scripts\dev.ps1 from the project root.'
