# V8.0: gera o JARVIS.exe (app para Windows com a ilha no topo) a partir de desktop\jarvis_desktop.py.
# PyInstaller + pywebview num ambiente separado (desktop\.venv), para não mexer no Python do JARVIS.
# Resultado: data\desktop\JARVIS.exe (o botão ⬇ APP PARA WINDOWS baixa daqui) e um atalho na Área de Trabalho.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Desk = Join-Path $Root "desktop"
$Venv = Join-Path $Desk ".venv"
$Out = Join-Path $Root "data\desktop"
$Work = Join-Path $Desk "build"

function Step($t) { Write-Host ""; Write-Host "  $t" -ForegroundColor Cyan }

Step "[1/5] Procurando o Python do JARVIS..."
$Py = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) { throw "Python nao encontrado. Instale o JARVIS primeiro (Instalar/Iniciar-JARVIS.bat)." }

Step "[2/5] Preparando o ambiente do app (so na primeira vez demora)..."
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) { & $Py -m venv $Venv }
$VPy = Join-Path $Venv "Scripts\python.exe"
& $VPy -m pip install --disable-pip-version-check -q --upgrade pip
& $VPy -m pip install --disable-pip-version-check -q "pywebview==5.3.2" "pyinstaller==6.11.1" "pillow==11.0.0"
if ($LASTEXITCODE -ne 0) { throw "Nao consegui instalar o pywebview/PyInstaller (precisa de internet)." }

Step "[3/5] Gravando a pasta do JARVIS e a versao no app..."
$Version = (Select-String -Path (Join-Path $Root "backend\version.py") -Pattern 'VERSION *= *"([0-9.]+)"').Matches[0].Groups[1].Value
$RootEsc = $Root.Replace("\", "\\")
Set-Content -Path (Join-Path $Desk "_build_info.py") -Encoding UTF8 -Value @"
# Gerado pelo build (scripts\desktop\build_exe.ps1). Nao edite.
JARVIS_ROOT = "$RootEsc"
VERSION = "$Version"
"@

Step "[4/5] Montando o JARVIS.exe (leva alguns minutos)..."
New-Item -ItemType Directory -Force -Path $Out, $Work | Out-Null
$Icon = Join-Path $Root "frontend\public\brand\avatar-512.png"
& $VPy -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon $Icon `
    --paths $Desk --hidden-import _build_info --distpath $Out --workpath $Work --specpath $Work `
    (Join-Path $Desk "jarvis_desktop.py")
if ($LASTEXITCODE -ne 0) { throw "O PyInstaller falhou. Veja a mensagem acima." }

Step "[5/5] Criando o atalho na Area de Trabalho..."
$Exe = Join-Path $Out "JARVIS.exe"
try {
  $Shell = New-Object -ComObject WScript.Shell
  $Lnk = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "JARVIS.lnk"))
  $Lnk.TargetPath = $Exe
  $Lnk.WorkingDirectory = $Out
  $Lnk.Description = "JARVIS - assistente pessoal"
  $Lnk.Save()
} catch { Write-Host "  (nao consegui criar o atalho; abra $Exe)" }

$Mb = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Write-Host ""
Write-Host "  [OK] JARVIS.exe pronto ($Mb MB): $Exe" -ForegroundColor Green
Write-Host "       Atalho 'JARVIS' na Area de Trabalho. Na central: botao APP PARA WINDOWS para baixar."
