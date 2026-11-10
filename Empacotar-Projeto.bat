@echo off
title J.A.R.V.I.S. - Empacotar Projeto para IA
color 0A

echo.
echo  ==============================================
echo    J.A.R.V.I.S. - EMPACOTAMENTO LIMPO
echo  ==============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\empacotar_projeto.ps1"
if errorlevel 1 (
    color 0C
    echo.
    echo  [ERRO] Ocorreu uma falha durante o empacotamento.
    echo.
)

pause
exit /b %errorlevel%
