@echo off
setlocal
title J.A.R.V.I.S. - Nao ligar mais com o Windows
color 0C

rem V8.11: apaga o atalho JARVIS da pasta Inicializar (o JARVIS continua funcionando pelo Iniciar-JARVIS.bat).

set "PY=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0backend\modules\autostart.py" remover
echo.
echo  [OK] O JARVIS nao liga mais sozinho com o Windows.
echo.
pause
exit /b 0
