@echo off
setlocal enabledelayedexpansion
title J.A.R.V.I.S. - Inicializacao
color 0B

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

rem V5.4.1: a central abre pelo site do Netlify (o mesmo endereco do celular e de qualquer PC).
rem O site conversa com o backend deste PC. No modo dev (Iniciar-JARVIS-Dev.bat) ou com
rem JARVIS_PAINEL_LOCAL=1, abre a interface local (http://127.0.0.1:5173) como antes.
set "SITE_URL=https://projeto-jarvis-ia.netlify.app/app/"
if "%JARVIS_DEV%"=="1" set "SITE_URL=http://127.0.0.1:5173/"
if "%JARVIS_PAINEL_LOCAL%"=="1" set "SITE_URL=http://127.0.0.1:5173/"
rem Parametro opcional "wake" (Ouvinte de Palmas): abre o painel ja iniciando o escaneamento facial.
set "OPEN_URL=%SITE_URL%"
set "WAKE="
if /i "%~1"=="wake" (
  set "WAKE=1"
  set "OPEN_URL=%SITE_URL%?wake=clap"
)
rem Parametro "site" (botao LIGAR O JARVIS da central do site, via Instalar-Botao-Ligar.bat):
rem liga tudo, mas nao abre aba nova; a central do site ja aberta reconecta sozinha.
set "FROM_SITE="
if /i "%~1"=="site" set "FROM_SITE=1"

echo.
echo  ==============================================
echo    J.A.R.V.I.S. - STARK OS
echo    Iniciando servicos em segundo plano
echo  ==============================================
echo.

rem V4.4: o backup diario agora roda DEPOIS de abrir o painel (no fim deste arquivo).

rem ---------- 1. Ambiente Python ----------
if not exist "%BACKEND%\venv\Scripts\python.exe" (
  echo  [1/5] Primeira execucao: criando ambiente virtual Python...
  where python >nul 2>nul
  if errorlevel 1 (
    echo  [ERRO] Python nao encontrado. Instale o Python 3.12 com PATH ativado.
    pause
    exit /b 1
  )
  python -m venv "%BACKEND%\venv"
  if errorlevel 1 (
    echo  [ERRO] Falha ao criar o ambiente Python.
    pause
    exit /b 1
  )
)

rem ---------- 2. Dependencias do Backend ----------
rem V5.6: tambem instala quando falta uma dependencia nova (ex.: icalendar, da agenda por iCal)
set "NEED_PIP="
if not exist "%BACKEND%\venv\Lib\site-packages\uvicorn" set "NEED_PIP=1"
if not exist "%BACKEND%\venv\Lib\site-packages\icalendar" set "NEED_PIP=1"
if defined NEED_PIP (
  echo  [2/5] Instalando dependencias do backend...
  "%BACKEND%\venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"
  if errorlevel 1 (
    echo  [ERRO] Falha ao instalar dependencias do backend.
    pause
    exit /b 1
  )
)

rem ---------- 3. Dependencias do Frontend ----------
if not exist "%FRONTEND%\node_modules\vite" (
  echo  [3/5] Instalando dependencias do frontend...
  where npm >nul 2>nul
  if errorlevel 1 (
    echo  [ERRO] Node.js/npm nao encontrado.
    pause
    exit /b 1
  )
  pushd "%FRONTEND%"
  call npm install
  popd
)

rem ---------- 4. Interface compilada (V4.4) ----------
rem Fora do modo dev, a interface roda ja compilada (frontend\dist) num servidor leve em Python:
rem sem Node e sem compilar a cada abertura. O build so e refeito quando o codigo mudou.
set "PY=%BACKEND%\venv\Scripts\python.exe"
set "SERVE=%ROOT%scripts\serve_frontend.py"
set "USE_VITE="
if "%JARVIS_DEV%"=="1" set "USE_VITE=1"
if not defined USE_VITE (
  "%PY%" "%SERVE%" --stale
  if errorlevel 1 (
    echo  [4/5] Interface mudou: gerando build novo ^(so desta vez^)...
    pushd "%FRONTEND%"
    call npm run build >nul
    if errorlevel 1 (
      echo  [AVISO] Build falhou. Usando o modo de desenvolvimento ^(mais lento^).
      set "USE_VITE=1"
    )
    popd
  )
)

rem ---------- Ja estava aberto? (V4.4) ----------
rem Se uma versao anterior ainda ocupa as portas, a nova falhava escondida e a antiga continuava.
rem Agora o Iniciar sempre substitui: encerra o que estiver nas portas 8000 e 5173 antes de subir.
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { Write-Host '  JARVIS ja estava aberto: reiniciando com a versao atual...'; $p | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; $d=(Get-Date).AddSeconds(8); while((Get-Date) -lt $d -and (Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue)){ Start-Sleep -Milliseconds 200 } }"

rem ---------- 5. Iniciar em segundo plano ----------
echo  [5/5] Iniciando backend e frontend...

set "RELOAD="
if "%JARVIS_DEV%"=="1" set "RELOAD=--reload"

rem V4.5: abre direto com a rede de casa (celular e app Android). Outros aparelhos ainda precisam da
rem chave de pareamento. Para ficar so neste PC: defina JARVIS_LOCAL=1 antes de rodar.
set "HOST=0.0.0.0"
set "NETMODE=true"
if "%JARVIS_LOCAL%"=="1" (
  set "HOST=127.0.0.1"
  set "NETMODE=false"
)
powershell -NoProfile -Command "$env:JARVIS_NETWORK_MODE='%NETMODE%'; Start-Process -FilePath '%PY%' -ArgumentList ('-m uvicorn main:app --host %HOST% --port 8000 ' + '%RELOAD%').Trim() -WorkingDirectory '%BACKEND%' -WindowStyle Hidden"

if defined USE_VITE (
  powershell -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c npm run dev -- --host %HOST%' -WorkingDirectory '%FRONTEND%' -WindowStyle Hidden"
) else (
  powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList 'serve_frontend.py --host %HOST% --port 5173' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden"
)

rem V6.3: ouvido offline ("Jarvis, ..." com o navegador fechado). So liga se o modelo Vosk estiver
rem baixado (%USERPROFILE%\.jarvis-voice). Fica quieto sozinho quando a central esta aberta numa aba do PC.
powershell -NoProfile -Command "$f=Join-Path '%ROOT%' 'logs\ouvido.pid'; if (Test-Path $f) { $i=Get-Content $f -ErrorAction SilentlyContinue; if ($i) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }; Remove-Item $f -ErrorAction SilentlyContinue }"
if exist "%USERPROFILE%\.jarvis-voice\vosk-model-small-pt-0.3" if exist "%BACKEND%\venv\Scripts\pythonw.exe" (
  powershell -NoProfile -Command "Start-Process -FilePath '%BACKEND%\venv\Scripts\pythonw.exe' -ArgumentList 'voice_listener.py' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden"
)

rem Abre o painel assim que backend e frontend responderem (ate 60 s), sem espera fixa.
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(60); while((Get-Date) -lt $d){ try { $null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/api/health'; $t=New-Object Net.Sockets.TcpClient('127.0.0.1',5173); $t.Close(); exit 0 } catch { Start-Sleep -Milliseconds 250 } }; exit 1"
rem V5.6.2: se uma aba do JARVIS ja estava aberta, ela reconecta sozinha em poucos segundos; nesse caso
rem nao abre outra (duas abas entrando juntas falavam duas vezes). Palmas (wake) sempre abrem.
set "TAB_OPEN="
if not defined WAKE if not defined FROM_SITE (
  powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(8); while((Get-Date) -lt $d){ try { $s=Invoke-RestMethod -TimeoutSec 2 'http://127.0.0.1:8000/api/lock/status'; if($s.devices -gt 0){ exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
  if not errorlevel 1 set "TAB_OPEN=1"
)
if defined TAB_OPEN echo  [OK] A central ja estava aberta numa aba: ela reconectou sozinha.
if not defined FROM_SITE if not defined TAB_OPEN start "" "%OPEN_URL%"

echo.
echo  ==============================================
echo    [OK] J.A.R.V.I.S. ATIVO EM SEGUNDO PLANO
echo    Pode fechar esta janela.
echo    Para parar, use o Parar-JARVIS.bat
echo  ==============================================
echo.

rem ---------- Backup Diario de Dados (depois de abrir, nao atrasa mais) ----------
if exist "%ROOT%Backup-Dados.bat" (
  call "%ROOT%Backup-Dados.bat" /silent
)
exit
