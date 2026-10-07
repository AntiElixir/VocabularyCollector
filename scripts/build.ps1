# Build the portable Windows app (run on Windows, from anywhere).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uv)) { throw "uv not found; install uv first." }

& $uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

& $uv run pyinstaller packaging/vocab-collector.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }

$dist = Join-Path $root "dist\VocabularyCollector"
New-Item -ItemType Directory -Force -Path (Join-Path $dist "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "data") | Out-Null
Copy-Item -Force (Join-Path $root "config\config.example.toml") (Join-Path $dist "config\config.example.toml")

Write-Host "Built $dist"
Write-Host "Next: copy config\config.example.toml to config\config.toml and paste your key."