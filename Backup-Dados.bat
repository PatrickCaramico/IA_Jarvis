@echo off
title JARVIS - Backup Diario de Dados
color 0B

set "IS_SILENT=0"
if "%1"=="/silent" set "IS_SILENT=1"
if "%1"=="--silent" set "IS_SILENT=1"

if "%IS_SILENT%"=="0" (
    echo.
    echo  ==============================================
    echo        J.A.R.V.I.S. - BACKUP DE DADOS
    echo  ==============================================
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\backup_dados.ps1"
    echo.
    echo  ----------------------------------------------
    echo  Backup finalizado com sucesso!
    pause
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\backup_dados.ps1" -Silent
)
