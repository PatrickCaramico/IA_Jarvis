@echo off
title J.A.R.V.I.S. - Encerrar Servicos
color 0C

echo.
echo  ==============================================
echo    J.A.R.V.I.S. - Encerrando servicos
echo  ==============================================
echo.

echo  Parando backend (porta 8000)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo  Parando frontend (porta 5173)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo  Parando o ouvido offline...
powershell -NoProfile -Command "$f=Join-Path '%~dp0' 'logs\ouvido.pid'; if (Test-Path $f) { $i=Get-Content $f -ErrorAction SilentlyContinue; if ($i) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }; Remove-Item $f -ErrorAction SilentlyContinue }"

echo.
echo  [OK] Servicos do JARVIS encerrados.
echo.
timeout /t 3 /nobreak >nul
exit
