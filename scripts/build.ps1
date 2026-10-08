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
$backupDir = Join-Path $root "dist\.backup"

if (Test-Path $dist) {
    if (Test-Path $backupDir) { Remove-Item -Recurse -Force $backupDir }
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    $dataSrc = Join-Path $dist "data"
    $dataDst = Join-Path $backupDir "data"
    if (Test-Path $dataSrc) {
        Copy-Item -Recurse -Force $dataSrc $dataDst
        Write-Host "Backed up data/"
    }

    $configSrc = Join-Path $dist "config\config.toml"
    $configDst = Join-Path $backupDir "config.toml"
    if (Test-Path $configSrc) {
        Copy-Item -Force $configSrc $configDst
        Write-Host "Backed up config/config.toml"
    }
}

& $uv run pyinstaller packaging/vocab-collector.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed. Backup preserved at $backupDir" -ForegroundColor Yellow
    throw "pyinstaller failed"
}

New-Item -ItemType Directory -Force -Path (Join-Path $dist "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "data") | Out-Null
Copy-Item -Force (Join-Path $root "config\config.example.toml") (Join-Path $dist "config\config.example.toml")

if (Test-Path $backupDir) {
    $dataBackup = Join-Path $backupDir "data"
    if (Test-Path $dataBackup) {
        $dataDst = Join-Path $dist "data"
        if (Test-Path $dataDst) { Remove-Item -Recurse -Force $dataDst }
        Copy-Item -Recurse -Force $dataBackup $dataDst
        Write-Host "Restored data/"
    }

    $configBackup = Join-Path $backupDir "config.toml"
    if (Test-Path $configBackup) {
        Copy-Item -Force $configBackup (Join-Path $dist "config\config.toml")
        Write-Host "Restored config/config.toml"
    }

    Remove-Item -Recurse -Force $backupDir
}

Write-Host "Built $dist"
