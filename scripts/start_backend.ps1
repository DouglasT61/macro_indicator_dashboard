param(
  [string]$ListenHost = '127.0.0.1',
  [int]$Port = 8000
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$env:PYTHONPATH = 'backend;vendor_py'
python -m uvicorn app.main:app --host $ListenHost --port $Port
