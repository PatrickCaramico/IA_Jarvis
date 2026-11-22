@echo off
setlocal
title J.A.R.V.I.S. - Ligar junto com o Windows
color 0B

rem V8.11: cria o atalho JARVIS na pasta Inicializar do seu usuario (sem administrador).
rem Ao entrar no Windows, o JARVIS liga sozinho em segundo plano (sem janela e sem abrir aba)
rem e o guardiao mantem ele ligado. Tambem da para ligar/desligar em Configuracoes, na central.
rem Para desfazer: Remover-JARVIS-do-Windows.bat

set "PY=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo  [ERRO] Abra o Iniciar-JARVIS.bat uma vez antes ^(ele prepara o ambiente^).
  pause
  exit /b 1
)
"%PY%" "%~dp0backend\modules\autostart.py" instalar
if errorlevel 1 (
  echo  [ERRO] Nao consegui criar o atalho na Inicializacao do Windows.
  pause
  exit /b 1
)
echo.
echo  [OK] O JARVIS vai ligar sozinho quando voce entrar no Windows.
echo  Para desfazer: Remover-JARVIS-do-Windows.bat
echo.
pause
exit /b 0
