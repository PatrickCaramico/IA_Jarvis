@echo off
setlocal
title J.A.R.V.I.S. - Instalar Ouvinte de Palmas no Windows
color 0B

rem Cria um atalho na pasta Inicializar do Windows: o Ouvinte de Palmas inicia ao entrar no Windows.
rem Para desfazer: Remover-Palmas-do-Windows.bat

set "ROOT=%~dp0"
set "PYW=%ROOT%backend\venv\Scripts\pythonw.exe"
if not exist "%PYW%" (
  echo  [ERRO] Ambiente Python nao encontrado. Rode o Iniciar-JARVIS.bat uma vez antes.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$lnk=[Environment]::GetFolderPath('Startup') + '\JARVIS Ouvinte de Palmas.lnk'; $s=(New-Object -ComObject WScript.Shell).CreateShortcut($lnk); $s.TargetPath='%PYW%'; $s.Arguments='\"%ROOT%scripts\clap_launcher.py\"'; $s.WorkingDirectory='%ROOT%'; $s.WindowStyle=7; $s.Description='JARVIS - Ouvinte de Palmas'; $s.Save()"
if errorlevel 1 (
  echo  [ERRO] Nao consegui criar o atalho de inicializacao.
  pause
  exit /b 1
)
echo  [OK] Ouvinte de Palmas registrado para iniciar com o Windows.
call "%ROOT%Iniciar-Palmas.bat"
exit /b 0
