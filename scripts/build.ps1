# Build the portable Windows app (run on Windows, from anywhere).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uv)) { throw "uv not found; install uv first." }

& $uv sync
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

$dist = Join-Path $root "dist\VocabularyCollector"
$backupDir = Join-Path $env:TEMP "vocab-collector-backup-$(Get-Random)"

if (Test-Path $dist) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    $dataSrc = Join-Path $dist "data"
    $dataDst = Join-Path $backupDir "data"
    if (Test-Path $dataSrc) {
        Copy-Item -Recurse -Force $dataSrc $dataDst
        Write-Host "Backed up data/ to $dataDst"
    }

    $configSrc = Join-Path $dist "config\config.toml"
    $configDst = Join-Path $backupDir "config.toml"
    if (Test-Path $configSrc) {
        Copy-Item -Force $configSrc $configDst
        Write-Host "Backed up config/config.toml to $configDst"
    }
}

& $uv run pyinstaller packaging/vocab-collector.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }

New-Item -ItemType Directory -Force -Path (Join-Path $dist "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "data") | Out-Null
Copy-Item -Force (Join-Path $root "config\config.example.toml") (Join-Path $dist "config\config.example.toml")

if (Test-Path $backupDir) {
    $dataBackup = Join-Path $backupDir "data"
    if (Test-Path $dataBackup) {
        Copy-Item -Recurse -Force $dataBackup (Join-Path $dist "data")
        Write-Host "Restored data/ from backup"
    }

    $configBackup = Join-Path $backupDir "config.toml"
    if (Test-Path $configBackup) {
        Copy-Item -Force $configBackup (Join-Path $dist "config\config.toml")
        Write-Host "Restored config/config.toml from backup"
    }

    Remove-Item -Recurse -Force $backupDir
}

Write-Host "Built $dist"
