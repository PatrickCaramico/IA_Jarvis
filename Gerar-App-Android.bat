@echo off
title J.A.R.V.I.S. - Gerar app Android
color 0B
echo.
echo  ==============================================
echo    J.A.R.V.I.S. - APP ANDROID (APK)
echo  ==============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\android\build_apk.ps1"
if errorlevel 1 (
  echo.
  echo  [ERRO] Nao consegui gerar o APK. Veja a mensagem acima.
  pause
  exit /b 1
)
echo.
echo  Pronto. Com o JARVIS aberto pelo Iniciar-JARVIS-Rede.bat, escaneie o QR
echo  da tela de bloqueio (modo Sentinela) com o celular para baixar o app.
echo.
pause
