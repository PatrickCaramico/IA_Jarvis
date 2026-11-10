@echo off
title JARVIS - Status do Sistema
color 0B

echo.
echo  ==============================================
echo        J.A.R.V.I.S. - STATUS ATUAL
echo  ==============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\status.ps1"

echo.
echo  ----------------------------------------------
echo  Pressione qualquer tecla para fechar...
pause > nul
