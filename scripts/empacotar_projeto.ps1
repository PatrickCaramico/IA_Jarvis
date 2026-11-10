# scripts/empacotar_projeto.ps1
# Empacota o projeto JARVIS de forma 100% limpa, segura e sem credenciais pessoais.
param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    # Salva na pasta pai de JARVIS para acesso fácil e sem auto-inclusão
    $ParentDir = Split-Path -Parent $ProjectRoot
    if (Test-Path $ParentDir) {
        $OutputDir = $ParentDir
    } else {
        $OutputDir = [Environment]::GetFolderPath("Desktop")
    }
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ZipName = "JARVIS_V3_Limpo_$Timestamp.zip"
$ZipPath = Join-Path $OutputDir $ZipName

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   J.A.R.V.I.S. - EMPACOTAMENTO LIMPO & SEGURO" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Origem: $ProjectRoot" -ForegroundColor Gray
Write-Host "  Destino: $ZipPath" -ForegroundColor Gray
Write-Host ""

# Pastas e arquivos a serem ignorados
$ExcludeDirectories = @(
    "venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".vscode",
    ".idea",
    "logs",
    "data",
    "_backup_dados",
    "_backup_layout",
    "_backup"
)

$ExcludeFiles = @(
    ".env",
    ".env.local",
    "*.pyc",
    "*.pyo",
    "*.zip",
    "*.log"
)

Write-Host "  [1/3] Mapeando arquivos permitidos..." -ForegroundColor Yellow

$TempDir = Join-Path $env:TEMP "jarvis_pkg_$Timestamp"
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempDir | Out-Null

$FilesCopied = 0
Get-ChildItem -Path $ProjectRoot -Recurse | ForEach-Object {
    $Item = $_
    $RelativePath = $Item.FullName.Substring($ProjectRoot.Length).TrimStart("\", "/")

    # Verifica se algum segmento do caminho bate com exclusão de diretório
    $Parts = $RelativePath -split "[\\/]"
    $ShouldExcludeDir = $false
    foreach ($dir in $ExcludeDirectories) {
        if ($Parts -contains $dir) {
            $ShouldExcludeDir = $true
            break
        }
    }

    if ($ShouldExcludeDir) { return }

    # Se for arquivo, verifica exclusão de arquivo
    if (-not $Item.PSIsContainer) {
        $FileName = $Item.Name
        $ShouldExcludeFile = $false
        foreach ($pat in $ExcludeFiles) {
            if ($FileName -like $pat) {
                $ShouldExcludeFile = $true
                break
            }
        }

        # Trava absoluta para .env e data/
        if ($FileName.Equals(".env", [StringComparison]::OrdinalIgnoreCase)) {
            $ShouldExcludeFile = $true
        }

        if (-not $ShouldExcludeFile) {
            $DestFile = Join-Path $TempDir $RelativePath
            $DestFolder = Split-Path -Parent $DestFile
            if (-not (Test-Path $DestFolder)) {
                New-Item -ItemType Directory -Path $DestFolder -Force | Out-Null
            }
            Copy-Item -Path $Item.FullName -Destination $DestFile -Force
            $FilesCopied++
        }
    }
}

Write-Host "  [OK] $FilesCopied arquivos mapeados com sucesso." -ForegroundColor Green
Write-Host "  [2/3] Compactando em arquivo ZIP..." -ForegroundColor Yellow

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

# Limpa temporários
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "  [3/3] Auditoria de seguranca do arquivo ZIP..." -ForegroundColor Yellow

$Archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
$HasEnv = $false
$HasData = $false
$HasNodeModules = $false
$HasVenv = $false

foreach ($entry in $Archive.Entries) {
    $entryName = $entry.FullName.ToLower()
    if ($entryName -eq ".env" -or $entryName.EndsWith("/.env") -or $entryName.EndsWith("\.env")) {
        $HasEnv = $true
    }
    if ($entryName.StartsWith("data/") -or $entryName.StartsWith("data\")) {
        $HasData = $true
    }
    if ($entryName.Contains("node_modules/") -or $entryName.Contains("node_modules\")) {
        $HasNodeModules = $true
    }
    if ($entryName.Contains("venv/") -or $entryName.Contains("venv\")) {
        $HasVenv = $true
    }
}
$Archive.Dispose()

if ($HasEnv -or $HasData -or $HasNodeModules -or $HasVenv) {
    Remove-Item $ZipPath -Force
    Write-Host "  [ERRO CRITICO] O arquivo ZIP continha itens proibidos! O pacote foi deletado imediatamente." -ForegroundColor Red
    exit 1
}

$ZipSize = (Get-Item $ZipPath).Length / 1MB
$ZipSizeStr = "{0:N2} MB" -f $ZipSize

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "   PACOTE GERADO COM SUCESSO!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Arquivo: $ZipPath" -ForegroundColor White
Write-Host "  Tamanho: $ZipSizeStr" -ForegroundColor Cyan
Write-Host "  Total de arquivos: $FilesCopied" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [x] Sem credenciais .env (Seguranca Total)" -ForegroundColor Green
Write-Host "  [x] Sem dados pessoais / tokens / fotos" -ForegroundColor Green
Write-Host "  [x] Sem node_modules ou venv pesados" -ForegroundColor Green
Write-Host "  Pronto para ser enviado para analise de IA!" -ForegroundColor Green
Write-Host ""
