@echo off
title J.A.R.V.I.S. - Remover Ouvinte de Palmas do Windows
color 0C
powershell -NoProfile -Command "Remove-Item -LiteralPath ([Environment]::GetFolderPath('Startup') + '\JARVIS Ouvinte de Palmas.lnk') -ErrorAction SilentlyContinue"
echo  [OK] Ouvinte de Palmas removido da inicializacao do Windows.
call "%~dp0Parar-Palmas.bat"
exit /b 0
