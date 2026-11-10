@echo off
title J.A.R.V.I.S. - Parar Ouvinte de Palmas
color 0C
echo.
echo  Encerrando o Ouvinte de Palmas e liberando o microfone...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*clap_launcher.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo  [OK] Ouvinte de Palmas encerrado.
timeout /t 3 /nobreak >nul
exit /b 0
