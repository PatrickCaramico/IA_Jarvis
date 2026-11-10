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

echo  Exibindo as últimas 50 linhas de logs...
echo  (Pressione Ctrl + C para sair do modo contínuo)
echo  ────────────────────────────────────────────────────────
echo.

powershell -NoProfile -Command "Get-Content -Path '%LOG_FILE%' -Tail 50 -Wait"

pause
