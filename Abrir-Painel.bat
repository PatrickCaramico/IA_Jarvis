@echo off
chcp 65001 > nul
title JARVIS — Abrir Painel
color 0B

rem V5.4.1: abre a central pelo site do Netlify (modo dev ou JARVIS_PAINEL_LOCAL=1: interface local)
set "SITE_URL=https://projeto-jarvis-ia.netlify.app/app/"
if "%JARVIS_DEV%"=="1" set "SITE_URL=http://127.0.0.1:5173/"
if "%JARVIS_PAINEL_LOCAL%"=="1" set "SITE_URL=http://127.0.0.1:5173/"
set "OPEN_URL=%SITE_URL%"
if /i "%~1"=="wake" set "OPEN_URL=%SITE_URL%?wake=clap"

echo.
echo  ==============================================
echo    J.A.R.V.I.S. - STARK OS
echo    Verificando status do painel...
echo  ==============================================
echo.

powershell -NoProfile -Command "$portOpen = $false; try { $tcp = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 5173); $portOpen = $true; $tcp.Close() } catch { $portOpen = $false }; if ($portOpen) { exit 0 } else { exit 1 }"

if errorlevel 1 (
    echo  [INFO] O JARVIS está desligado.
    echo  Iniciando serviços em segundo plano...
    echo.
    call "%~dp0Iniciar-JARVIS.bat" %1
) else (
    echo  [OK] JARVIS já está em execução!
    echo  Abrindo o painel no navegador...
    start "" "%OPEN_URL%"
    timeout /t 2 /nobreak >nul
    exit
)
