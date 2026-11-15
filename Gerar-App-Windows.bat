@echo off
title J.A.R.V.I.S. - Gerar app para Windows
color 0B
echo.
echo  ==============================================
echo    J.A.R.V.I.S. - APP PARA WINDOWS (atalho JARVIS)
echo  ==============================================
echo   Janela propria com o Modo Desk, a ilha no topo
echo   da tela e a tecla para falar com o JARVIS.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\desktop\build_exe.ps1"
if errorlevel 1 (
  echo.
  echo  [ERRO] Nao consegui instalar o app. Veja a mensagem acima.
  pause
  exit /b 1
)
echo.
echo  Pronto. Abra pelo atalho JARVIS na Area de Trabalho.
echo.
pause
