@echo off
setlocal
set "BACKEND=%~dp0backend"

echo ==== Diagnostico do backend do JARVIS ====
echo Pasta: %BACKEND%
echo.

if not exist "%BACKEND%\venv\Scripts\python.exe" (
  echo [ERRO] Nao encontrei o ambiente Python em backend\venv.
  echo Coloque este arquivo na mesma pasta do Iniciar-JARVIS.bat.
  pause
  exit /b 1
)

echo Verificando se a porta 8000 esta ocupada...
netstat -ano | findstr ":8000" | findstr "LISTENING"
echo.

cd /d "%BACKEND%"
echo Iniciando o backend. Copie o ERRO que aparecer abaixo, se houver:
echo ----------------------------------------------------------------
"%BACKEND%\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
echo ----------------------------------------------------------------
echo O backend foi encerrado. Veja a mensagem acima.
pause
endlocal
