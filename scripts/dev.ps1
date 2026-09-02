$ErrorActionPreference = 'Stop'
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$BackendRoot = Join-Path $ProjectRoot 'backend'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$BackendPython = Join-Path $BackendRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $BackendPython)) {
    throw 'Backend environment is missing. Run scripts\setup.ps1 first.'
}

$Backend = Start-Process -FilePath $BackendPython `
    -ArgumentList '-m','uvicorn','app.main:app','--reload','--host','127.0.0.1','--port','8000' `
    -WorkingDirectory $BackendRoot -WindowStyle Hidden -PassThru

try {
    Set-Location $FrontendRoot
    npm run dev
}
finally {
    if (-not $Backend.HasExited) {
        Stop-Process -Id $Backend.Id
    }
}
