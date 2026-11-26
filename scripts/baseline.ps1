[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BaselineArguments
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $PSScriptRoot "baseline.py") @BaselineArguments
exit $LASTEXITCODE
