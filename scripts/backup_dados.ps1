param (
    [switch]$Silent = $false
)

$rootDir = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $rootDir "data"
$backupBaseDir = Join-Path $rootDir "_backup_dados"

if (-not (Test-Path $dataDir)) {
    if (-not $Silent) {
        Write-Host "  [AVISO] Pasta 'data' nao encontrada em: $dataDir" -ForegroundColor Yellow
    }
    exit 0
}

# Criar pasta base de backup se nao existir
if (-not (Test-Path $backupBaseDir)) {
    New-Item -ItemType Directory -Path $backupBaseDir -Force | Out-Null
}

$todayFolder = Get-Date -Format "yyyy-MM-dd"
$targetBackupDir = Join-Path $backupBaseDir $todayFolder

if (-not (Test-Path $targetBackupDir)) {
    New-Item -ItemType Directory -Path $targetBackupDir -Force | Out-Null
}

# Copiar dados
Copy-Item -Path (Join-Path $dataDir "*") -Destination $targetBackupDir -Recurse -Force

if (-not $Silent) {
    Write-Host "  [OK] Backup dos dados salvo em: _backup_dados\$todayFolder" -ForegroundColor Green
}

# Manter apenas os 7 dias mais recentes
$allBackups = Get-ChildItem -Path $backupBaseDir -Directory | Sort-Object Name -Descending
if ($allBackups.Count -gt 7) {
    $toRemove = $allBackups | Select-Object -Skip 7
    foreach ($oldFolder in $toRemove) {
        Remove-Item -Path $oldFolder.FullName -Recurse -Force
        if (-not $Silent) {
            Write-Host ("  [LIMPEZA] Backup antigo removido: " + $oldFolder.Name) -ForegroundColor DarkGray
        }
    }
}
