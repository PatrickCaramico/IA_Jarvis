@echo off
chcp 65001 > nul
title JARVIS — Atualizar Dependências e Build Frontend
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║          J.A.R.V.I.S. — FRONTEND: SETUP / BUILD       ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0frontend"

echo  [1/2] Verificando dependências do frontend (npm install)...
call npm install
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao instalar dependências.
    pause
    exit /b 1
)

echo.
echo  [2/2] Gerando build de produção (npm run build)...
call npm run build
if errorlevel 1 (
    echo.
    echo  [ERRO] Build falhou. Verifique os erros acima.
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  [OK] Build concluído com sucesso em frontend/dist!  ║
echo  ║  V4.4: o Iniciar-JARVIS.bat usa este build e refaz   ║
echo  ║  sozinho quando o código muda. Ao vivo: modo Dev.    ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause
