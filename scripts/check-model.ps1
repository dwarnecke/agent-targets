param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Path)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Path) {
    $Path = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'runs') -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'model') } | ForEach-Object FullName)
}

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = 'python'
}

# Run from the source tree so the check needs no installed package
$env:PYTHONPATH = Join-Path $projectRoot 'src'
& $python -m agent_targets.workbook @Path
exit $LASTEXITCODE
