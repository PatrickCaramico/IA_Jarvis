@echo off
setlocal enabledelayedexpansion
title J.A.R.V.I.S. - Inicializacao
color 0B

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
rem V8.11: sinal de "ligando/atualizando" para o guardiao nao religar no meio (apagado no fim)
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
> "%ROOT%logs\iniciando.flag" echo %date% %time%

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
rem V9.5.3: parametro "atualizar" (botao ATUALIZAR E LIGAR da tela Reconectando, atalho jarvis://atualizar):
rem baixa a versao nova antes de ligar. Com o JARVIS fora do ar, a central nao tinha como atualizar.
set "UPDATE_FIRST="
if /i "%~1"=="atualizar" (
  set "FROM_SITE=1"
  set "UPDATE_FIRST=1"
)

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

rem V9.5.3: atualiza antes de conferir as dependencias (a versao nova pode trazer biblioteca nova)
if defined UPDATE_FIRST (
  echo  [1/5] Baixando a versao mais nova...
  "%BACKEND%\venv\Scripts\python.exe" "%ROOT%scripts\atualizar_jarvis.py"
)

rem ---------- 2. Dependencias do Backend ----------
rem V5.6: tambem instala quando falta uma dependencia nova (ex.: icalendar, da agenda por iCal)
set "NEED_PIP="
if not exist "%BACKEND%\venv\Lib\site-packages\uvicorn" set "NEED_PIP=1"
if not exist "%BACKEND%\venv\Lib\site-packages\icalendar" set "NEED_PIP=1"
rem V7.7: certificado da conexao criptografada (https) na rede de casa
if not exist "%BACKEND%\venv\Lib\site-packages\cryptography" set "NEED_PIP=1"
rem V9.5.2: uma atualizacao com biblioteca nova derrubava o backend ao ligar (so as 3 acima eram conferidas).
rem Agora instala sempre que o requirements.txt mudou (impressao digital guardada em venv\.jarvis-req.sha).
set "REQ_SUM="
for /f "skip=1 delims=" %%h in ('certutil -hashfile "%BACKEND%\requirements.txt" SHA256 2^>nul') do if not defined REQ_SUM set "REQ_SUM=%%h"
set "REQ_OLD="
if exist "%BACKEND%\venv\.jarvis-req.sha" set /p REQ_OLD=<"%BACKEND%\venv\.jarvis-req.sha"
if defined REQ_SUM if not "%REQ_SUM%"=="%REQ_OLD%" set "NEED_PIP=1"
if defined NEED_PIP (
  echo  [2/5] Instalando dependencias do backend...
  "%BACKEND%\venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%BACKEND%\requirements.txt"
  if errorlevel 1 (
    echo  [ERRO] Falha ao instalar dependencias do backend.
    pause
    exit /b 1
  )
  if defined REQ_SUM (> "%BACKEND%\venv\.jarvis-req.sha" echo %REQ_SUM%)
)

set "PY=%BACKEND%\venv\Scripts\python.exe"
rem ---------- Ja estava aberto? (V4.4) ----------
rem Se uma versao anterior ainda ocupa as portas, a nova falhava escondida e a antiga continuava.
rem Agora o Iniciar sempre substitui: encerra o que estiver na porta 8000 (e, mais abaixo, na 5173) antes de subir.
rem V9.4.1: o PowerShell so abre se algo ja ocupa a porta. Logo depois de ligar o PC, so abrir o PowerShell
rem levava alguns segundos, e quase sempre nao havia nada para encerrar. Porta escutando = endereco remoto 0.0.0.0:0
rem (o netstat traduz a palavra LISTENING no Windows em portugues, por isso nao dependemos dela).
netstat -ano -p tcp | findstr /r /c:":8000  *0\.0\.0\.0:0 " /c:":8443  *0\.0\.0\.0:0 " >nul 2>nul
if not errorlevel 1 (
  powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8000,8443 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { Write-Host '  JARVIS ja estava aberto: reiniciando com a versao atual...'; $p | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; $d=(Get-Date).AddSeconds(8); while((Get-Date) -lt $d -and (Get-NetTCPConnection -LocalPort 8000,8443 -State Listen -ErrorAction SilentlyContinue)){ Start-Sleep -Milliseconds 200 } }"
)

rem ---------- 3. Backend (V9.4: liga ANTES de conferir a interface local) ----------
rem A central abre pelo site do Netlify e so precisa do backend. Antes, o backend so subia depois de conferir,
rem baixar (ate 20 s) ou montar a interface local, e a central ficava "procurando" o PC por um minuto.
echo  [3/5] Ligando o backend...

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
rem V7.7: run_server.py = o mesmo backend, mais o https da rede de casa quando ele esta ligado
if defined RELOAD (
  powershell -NoProfile -Command "$env:JARVIS_NETWORK_MODE='%NETMODE%'; Start-Process -FilePath '%PY%' -ArgumentList ('-m uvicorn main:app --host %HOST% --port 8000 ' + '%RELOAD%').Trim() -WorkingDirectory '%BACKEND%' -WindowStyle Hidden"
) else (
  powershell -NoProfile -Command "$env:JARVIS_NETWORK_MODE='%NETMODE%'; Start-Process -FilePath '%PY%' -ArgumentList 'run_server.py --host %HOST% --port 8000' -WorkingDirectory '%BACKEND%' -WindowStyle Hidden"
)

rem V8.1.5: edge-tts antigo nao fala mais (a Microsoft mudou o servico de voz): atualiza sozinho.
rem V9.4.1: conferido DEPOIS de ligar o backend (antes, abrir o Python so para isso atrasava a subida).
"%PY%" -c "import importlib.metadata as m,sys; v=m.version('edge-tts').split('.'); sys.exit(0 if (int(v[0]),int(v[1]))>=(7,3) else 1)" >nul 2>nul
if errorlevel 1 (
  echo  [3/5] Atualizando a voz do JARVIS ^(edge-tts^)...
  "%PY%" -m pip install --disable-pip-version-check -q -U "edge-tts>=7.3.0"
)

rem ---------- 4. Dependencias do Frontend ----------
if not exist "%FRONTEND%\node_modules\vite" (
  echo  [4/5] Instalando dependencias do frontend...
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

rem ---------- 5. Interface compilada (V4.4) ----------
rem Fora do modo dev, a interface roda ja compilada (frontend\dist) num servidor leve em Python:
rem sem Node e sem compilar a cada abertura. O build so e refeito quando o codigo mudou.
set "PY=%BACKEND%\venv\Scripts\python.exe"
set "SERVE=%ROOT%scripts\serve_frontend.py"
set "USE_VITE="
if "%JARVIS_DEV%"=="1" set "USE_VITE=1"
if not defined USE_VITE (
  "%PY%" "%SERVE%" --stale
  if errorlevel 1 (
    rem V8.2.2: primeiro tenta baixar a interface pronta do site (segundos); se nao der, monta aqui (minutos)
    echo  [5/5] Interface mudou: baixando a versao pronta...
    set "JARVIS_PREBUILT_WAIT=20"
    "%PY%" "%ROOT%scripts\prebuilt.py" "%FRONTEND%"
  )
  "%PY%" "%SERVE%" --stale
  if errorlevel 1 (
    rem V8.2.3: com uma interface ja montada, o JARVIS LIGA NA HORA com ela e a nova e montada em segundo
    rem plano (antes o JARVIS ficava desligado os minutos todos da montagem e a atualizacao parecia travada)
    if exist "%FRONTEND%\dist\index.html" (
      echo  [5/5] Interface nova sera montada em segundo plano ^(o JARVIS ja liga com a atual^)...
      set "BUILD_LATER=1"
    ) else (
      echo  [5/5] Primeira vez: montando a interface ^(alguns minutos^)...
      pushd "%FRONTEND%"
      call npm run build >nul
      if errorlevel 1 (
        echo  [AVISO] Build falhou. Usando o modo de desenvolvimento ^(mais lento^).
        set "USE_VITE=1"
      )
      popd
    )
  )
)

rem Interface local (porta 5173): encerra a anterior, se houver, e sobe a atual
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 5173,5443 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { $p | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; $d=(Get-Date).AddSeconds(8); while((Get-Date) -lt $d -and (Get-NetTCPConnection -LocalPort 5173,5443 -State Listen -ErrorAction SilentlyContinue)){ Start-Sleep -Milliseconds 200 } }"
if defined USE_VITE (
  powershell -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c npm run dev -- --host %HOST%' -WorkingDirectory '%FRONTEND%' -WindowStyle Hidden"
) else (
  powershell -NoProfile -Command "$p=Start-Process -FilePath '%PY%' -ArgumentList 'serve_frontend.py --host %HOST% --port 5173' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden -PassThru; try { $p.PriorityClass='BelowNormal' } catch {}"
)

rem V8.2.3: a interface nova e montada em segundo plano, com o JARVIS ja ligado (registro em logs\build.log)
if defined BUILD_LATER (
  powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList 'build_background.py' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden"
)

rem V6.3: ouvido offline ("Jarvis, ..." com o navegador fechado). So liga se o modelo Vosk estiver
rem baixado (%USERPROFILE%\.jarvis-voice). Fica quieto sozinho quando a central esta aberta numa aba do PC.
powershell -NoProfile -Command "$f=Join-Path '%ROOT%' 'logs\ouvido.pid'; if (Test-Path $f) { $i=Get-Content $f -ErrorAction SilentlyContinue; if ($i) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }; Remove-Item $f -ErrorAction SilentlyContinue }"
if exist "%USERPROFILE%\.jarvis-voice\vosk-model-small-pt-0.3" if exist "%BACKEND%\venv\Scripts\pythonw.exe" (
  powershell -NoProfile -Command "$p=Start-Process -FilePath '%BACKEND%\venv\Scripts\pythonw.exe' -ArgumentList 'voice_listener.py' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden -PassThru; try { $p.PriorityClass='BelowNormal' } catch {}"
)

rem V8.11: guardiao (mantem o JARVIS ligado: religa se ele cair sozinho). Troca o antigo, se houver.
powershell -NoProfile -Command "$f=Join-Path '%ROOT%' 'logs\guardiao.pid'; if (Test-Path $f) { $i=Get-Content $f -ErrorAction SilentlyContinue; if ($i) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }; Remove-Item $f -ErrorAction SilentlyContinue }"
if exist "%BACKEND%\venv\Scripts\pythonw.exe" (
  powershell -NoProfile -Command "$p=Start-Process -FilePath '%BACKEND%\venv\Scripts\pythonw.exe' -ArgumentList 'guardiao.py' -WorkingDirectory '%ROOT%scripts' -WindowStyle Hidden -PassThru; try { $p.PriorityClass='BelowNormal' } catch {}"
)

rem Abre o painel assim que backend e frontend responderem (ate 60 s), sem espera fixa.
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(60); while((Get-Date) -lt $d){ try { $null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/api/health'; $t=New-Object Net.Sockets.TcpClient('127.0.0.1',5173); $t.Close(); exit 0 } catch { Start-Sleep -Milliseconds 250 } }; exit 1"
rem V9.5.2: nao respondeu? O socorro espera mais um pouco, le o motivo (logs\backend-erro.log) e resolve o que da
rem (biblioteca faltando: instala e liga de novo). Antes o JARVIS ficava fora do ar em silencio.
if errorlevel 1 (
  echo  [!] O JARVIS ainda nao respondeu: conferindo o motivo...
  "%PY%" "%ROOT%scripts\socorro_subida.py" "%HOST%" "%NETMODE%"
)
rem V5.6.2: se uma aba do JARVIS ja estava aberta, ela reconecta sozinha em poucos segundos; nesse caso
rem nao abre outra (duas abas entrando juntas falavam duas vezes). Palmas (wake) sempre abrem.
set "TAB_OPEN="
if not defined WAKE if not defined FROM_SITE (
  powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(8); while((Get-Date) -lt $d){ try { $s=Invoke-RestMethod -TimeoutSec 2 'http://127.0.0.1:8000/api/lock/status'; if($s.devices -gt 0){ exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
  if not errorlevel 1 set "TAB_OPEN=1"
)
if defined TAB_OPEN echo  [OK] A central ja estava aberta numa aba: ela reconectou sozinha.
if not defined FROM_SITE if not defined TAB_OPEN start "" "%OPEN_URL%"

del "%ROOT%logs\iniciando.flag" >nul 2>nul

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
