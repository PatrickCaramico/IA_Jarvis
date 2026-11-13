@echo off
title J.A.R.V.I.S. - Preparar app no GitHub
color 0B
echo.
echo  ==============================================
echo    J.A.R.V.I.S. - APP QUE SE ATUALIZA SOZINHO
echo  ==============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\android\preparar_github.ps1"
if errorlevel 1 (
  echo.
  echo  [ERRO] Veja a mensagem acima.
)
echo.
pause
