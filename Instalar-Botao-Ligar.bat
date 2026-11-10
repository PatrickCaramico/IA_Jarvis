@echo off
setlocal
title J.A.R.V.I.S. - Instalar botao LIGAR O JARVIS do site
color 0B

rem Cria o atalho jarvis:// so para o seu usuario do Windows (sem administrador).
rem Com ele, o botao "LIGAR O JARVIS" da central do site liga o JARVIS deste PC.
rem O que o atalho faz: roda o Iniciar-JARVIS.bat no modo "site" (liga o backend, sem abrir aba nova).
rem O endereco que o site manda e ignorado: o atalho nao executa mais nada alem disso.
rem O navegador sempre pergunta antes de abrir (a menos que voce marque "sempre permitir").
rem Para desfazer: Remover-Botao-Ligar.bat

set "JARVIS_START=%~dp0Iniciar-JARVIS.bat"
if not exist "%JARVIS_START%" (
  echo  [ERRO] Iniciar-JARVIS.bat nao encontrado nesta pasta.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$k='HKCU:\Software\Classes\jarvis'; New-Item -Path $k -Force | Out-Null; Set-Item -Path $k -Value 'URL:JARVIS'; New-ItemProperty -Path $k -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null; $c=New-Item -Path ($k + '\shell\open\command') -Force; Set-Item -Path ($k + '\shell\open\command') -Value ('\"' + $env:ComSpec + '\" /c \"\"' + $env:JARVIS_START + '\" site\"')"
if errorlevel 1 (
  echo  [ERRO] Nao consegui criar o atalho jarvis://.
  pause
  exit /b 1
)

echo.
echo  [OK] Botao LIGAR O JARVIS ativado.
echo  Na central do site, com o JARVIS desligado, toque em LIGAR O JARVIS
echo  e permita abrir o programa. Para desfazer: Remover-Botao-Ligar.bat
echo.
pause
exit /b 0
