$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

Push-Location (Join-Path $ProjectRoot 'backend')
try {
    if (-not (Test-Path '.venv')) {
        py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Creating the Python environment failed.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -e '.[dev,ui]'
    if ($LASTEXITCODE -ne 0) { throw 'Installing Python dependencies failed.' }
    if (-not (Test-Path '.env')) {
        Copy-Item '.env.example' '.env'
    }
}
finally {
    Pop-Location
}

Write-Host 'Setup complete. Run scripts\dev.ps1 from the project root.'
