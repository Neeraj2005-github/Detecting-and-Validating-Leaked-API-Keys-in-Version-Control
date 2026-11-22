$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found at $python. Create .venv and install requirements.txt first."
}

$npmCommand = Get-Command npm.cmd -ErrorAction Stop
$backend = $null
$frontend = $null
try {
    $backend = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $root -PassThru
    $frontend = Start-Process -FilePath $npmCommand.Source -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173') -WorkingDirectory (Join-Path $root 'frontend') -PassThru

    foreach ($endpoint in @(
        @{ Url = 'http://127.0.0.1:8000/health'; Process = $backend; Name = 'backend' },
        @{ Url = 'http://127.0.0.1:5173/vaultguard/scanner'; Process = $frontend; Name = 'frontend' }
    )) {
        $ready = $false
        for ($attempt = 0; $attempt -lt 45; $attempt++) {
            if ($endpoint.Process.HasExited) {
                throw "The $($endpoint.Name) process exited before becoming ready."
            }
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $endpoint.Url -TimeoutSec 2
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                    $ready = $true
                    break
                }
            }
            catch {
                Start-Sleep -Seconds 1
            }
        }
        if (-not $ready) {
            throw "The $($endpoint.Name) did not become ready at $($endpoint.Url)."
        }
    }

    Start-Process 'http://127.0.0.1:5173/vaultguard/scanner'
    Write-Output "Demo ready: http://127.0.0.1:5173/vaultguard/scanner"
    Write-Output "Backend PID: $($backend.Id); frontend PID: $($frontend.Id)"
}
catch {
    if ($frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id
    }
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id
    }
    throw
}
