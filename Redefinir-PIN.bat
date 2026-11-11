@echo off
setlocal
title J.A.R.V.I.S. - Redefinir PIN (ultimo recurso)
color 0E

rem V5.1: ultimo recurso quando o PIN foi esquecido E o rosto nao funciona (camera quebrada).
rem O jeito normal e pelo rosto: na tela de bloqueio, "Esqueci o PIN" (ou Configuracoes > Bloqueio).
rem Este arquivo apaga o PIN do dono (data\lock_pin.json). Uma copia fica em data\lock_pin.antigo.json.
rem Sem PIN, a entrada volta a ser so pelo rosto ate voce criar outro em Configuracoes > Bloqueio.
rem PIN de outras pessoas: data\perfis\<pessoa>\lock_pin.json (apague o arquivo da pessoa).

set "PINFILE=%~dp0data\lock_pin.json"
if not exist "%PINFILE%" (
  echo.
  echo  O dono nao tem PIN cadastrado. Nada a fazer.
  echo.
  pause
  exit /b 0
)

echo.
echo  Isto apaga o PIN do dono do JARVIS.
echo  Depois, crie um PIN novo em Configuracoes ^> Bloqueio.
echo.
set /p "OK=Digite SIM para continuar: "
if /i not "%OK%"=="SIM" (
  echo  Cancelado. Nada foi alterado.
  pause
  exit /b 0
)

copy /y "%PINFILE%" "%~dp0data\lock_pin.antigo.json" >nul
del /q "%PINFILE%"
if exist "%PINFILE%" (
  echo  [ERRO] Nao consegui apagar o PIN. Feche o JARVIS e tente de novo.
  pause
  exit /b 1
)
echo.
echo  [OK] PIN apagado. Entre pelo rosto e crie um novo em Configuracoes ^> Bloqueio.
echo.
pause
exit /b 0
