@echo off
setlocal
title J.A.R.V.I.S. - Ouvinte de Palmas
color 0B

rem Inicia o Ouvinte de Palmas em segundo plano (pythonw, sem janela).
rem Duas palmas com o JARVIS fechado: liga os servicos, abre o painel e inicia o leitor facial.
rem O microfone fica em uso enquanto o ouvinte estiver ativo. Para parar: Parar-Palmas.bat

set "ROOT=%~dp0"
set "PY=%ROOT%backend\venv\Scripts\python.exe"
set "PYW=%ROOT%backend\venv\Scripts\pythonw.exe"

if not exist "%PY%" (
  echo  [ERRO] Ambiente Python nao encontrado. Rode o Iniciar-JARVIS.bat uma vez antes.
  pause
  exit /b 1
)

"%PY%" -c "import sounddevice, numpy" >nul 2>nul
if errorlevel 1 (
  echo  Instalando dependencias do Ouvinte de Palmas ^(sounddevice^)...
  "%PY%" -m pip install -r "%ROOT%scripts\requirements-clap.txt"
  if errorlevel 1 (
    echo  [ERRO] Falha ao instalar a biblioteca sounddevice.
    pause
    exit /b 1
  )
)

powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*clap_launcher.py*' }) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
  echo  [OK] O Ouvinte de Palmas ja esta ativo.
  timeout /t 3 /nobreak >nul
  exit /b 0
)

start "" /D "%ROOT%." "%PYW%" "%ROOT%scripts\clap_launcher.py"
echo.
echo  [OK] Ouvinte de Palmas ativo em segundo plano.
echo  Bata 2 palmas com o JARVIS fechado para ligar e iniciar o leitor facial.
echo  Log: logs\clap_launcher.log   Ajustes: data\clap_launcher.json
echo  Para testar a sensibilidade: backend\venv\Scripts\python.exe scripts\clap_launcher.py --test
echo.
timeout /t 5 /nobreak >nul
exit /b 0
