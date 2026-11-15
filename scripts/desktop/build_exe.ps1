# V8.1.1: instala o APP DO JARVIS para Windows (janela propria + ilha no topo + tecla para falar).
# Antes (8.0) era um JARVIS.exe montado pelo PyInstaller em modo "onefile", e antivirus como o McAfee
# acusavam como virus (falso positivo: exe novo, sem assinatura, que se descompacta na pasta TEMP).
# Agora NAO existe exe novo: o atalho "JARVIS" abre o app com o pythonw.exe oficial do Python
# (assinado pela Python Software Foundation, conhecido pelos antivirus). Nada e baixado pelo navegador.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Desk = Join-Path $Root "desktop"
$Venv = Join-Path $Desk ".venv"
$Out = Join-Path $Root "data\desktop"

function Step($t) { Write-Host ""; Write-Host "  $t" -ForegroundColor Cyan }

Step "[1/4] Procurando o Python do JARVIS..."
$Py = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) { throw "Python nao encontrado. Instale o JARVIS primeiro (Instalar/Iniciar-JARVIS.bat)." }

Step "[2/4] Preparando o ambiente do app (so na primeira vez demora)..."
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) { & $Py -m venv $Venv }
$VPy = Join-Path $Venv "Scripts\python.exe"
$VPyw = Join-Path $Venv "Scripts\pythonw.exe"
& $VPy -m pip install --disable-pip-version-check -q --upgrade pip
& $VPy -m pip install --disable-pip-version-check -q "pywebview==5.3.2" "pillow==11.0.0"
if ($LASTEXITCODE -ne 0) { throw "Nao consegui instalar o pywebview (precisa de internet)." }

Step "[3/4] Criando o icone e removendo o JARVIS.exe antigo..."
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Png = Join-Path $Root "frontend\public\brand\avatar-512.png"
$Ico = Join-Path $Desk "jarvis.ico"
& $VPy -c "import sys; from PIL import Image; Image.open(sys.argv[1]).save(sys.argv[2], sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" $Png $Ico
foreach ($Old in @((Join-Path $Out "JARVIS.exe"), (Join-Path $Desk "build"), (Join-Path $Desk "_build_info.py"))) {
  if (Test-Path $Old) { Remove-Item -Recurse -Force $Old -ErrorAction SilentlyContinue }
}

Step "[4/4] Criando o atalho JARVIS (Area de Trabalho e Menu Iniciar)..."
$Script = Join-Path $Desk "jarvis_desktop.py"
$Shell = New-Object -ComObject WScript.Shell
$Places = @([Environment]::GetFolderPath("Desktop"), (Join-Path ([Environment]::GetFolderPath("Programs")) ""))
foreach ($Dir in $Places) {
  $Lnk = $Shell.CreateShortcut((Join-Path $Dir "JARVIS.lnk"))
  $Lnk.TargetPath = $VPyw
  $Lnk.Arguments = '"' + $Script + '"'
  $Lnk.WorkingDirectory = $Desk
  $Lnk.IconLocation = $Ico
  $Lnk.Description = "JARVIS - assistente pessoal"
  $Lnk.Save()
}
$Version = (Select-String -Path (Join-Path $Root "backend\version.py") -Pattern 'VERSION *= *"([0-9.]+)"').Matches[0].Groups[1].Value
$Info = @{ versao = $Version; instalado_em = (Get-Date -Format "dd/MM/yyyy HH:mm"); atalho = (Join-Path $Places[0] "JARVIS.lnk") } | ConvertTo-Json
Set-Content -Path (Join-Path $Out "app.json") -Encoding UTF8 -Value $Info

Write-Host ""
Write-Host "  [OK] App do JARVIS instalado." -ForegroundColor Green
Write-Host "       Abra pelo atalho 'JARVIS' na Area de Trabalho ou no Menu Iniciar."
Write-Host "       (Sem exe novo: o antivirus nao tem o que bloquear.)"
