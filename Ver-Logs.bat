@echo off
chcp 65001 > nul
title JARVIS — Visualizador de Logs
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║             J.A.R.V.I.S. — LOGS DO SISTEMA           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

set "LOG_FILE=%~dp0logs\jarvis.log"

if not exist "%LOG_FILE%" (
    echo  [AVISO] O arquivo de logs ainda não existe.
    echo  Caminho esperado: %LOG_FILE%
    echo  Inicie o JARVIS para começar a gerar registros.
    echo.
    pause
    exit /b 0
)

rem V9.5.2: se o JARVIS caiu ao ligar, o motivo e o que o PC tentou para religar aparecem primeiro
if exist "%~dp0logs\backend-erro.log" (
    echo  ÚLTIMA QUEDA AO LIGAR - logs\backend-erro.log:
    powershell -NoProfile -Command "Get-Content -Path '%~dp0logs\backend-erro.log' -Tail 20"
    echo.
)
if exist "%~dp0logs\ligar.log" (
    echo  LIGAR E RELIGAR - logs\ligar.log:
    powershell -NoProfile -Command "Get-Content -Path '%~dp0logs\ligar.log' -Tail 8"
    echo.
)

echo  Exibindo as últimas 50 linhas de logs...
echo  (Pressione Ctrl + C para sair do modo contínuo)
echo  ────────────────────────────────────────────────────────
echo.

powershell -NoProfile -Command "Get-Content -Path '%LOG_FILE%' -Tail 50 -Wait"

pause
