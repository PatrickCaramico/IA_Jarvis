@echo off
setlocal
title J.A.R.V.I.S. - Instalar botao LIGAR O JARVIS do site
color 0B

rem Cria o atalho jarvis:// so para o seu usuario do Windows (sem administrador).
rem Com ele, o botao "LIGAR O JARVIS" da central do site liga o JARVIS deste PC.
rem O que o atalho faz: roda o Iniciar-JARVIS.bat no modo "site" (liga o backend, sem abrir aba nova) ou, com
rem jarvis://atualizar, no modo "atualizar" (baixa a versao nova e liga). Nao executa mais nada alem disso.
rem O navegador sempre pergunta antes de abrir (a menos que voce marque "sempre permitir").
rem Para desfazer: Remover-Botao-Ligar.bat

set "JARVIS_START=%~dp0Iniciar-JARVIS.bat"
rem V9.5.3: o atalho chama o ligar_jarvis.py, que entende jarvis://atualizar (atualiza e liga) e qualquer outro
rem endereco como "ligar". O endereco nunca vira comando: so escolhe uma dessas duas opcoes fixas.
set "JARVIS_PYW=%~dp0backend\venv\Scripts\pythonw.exe"
set "JARVIS_LIGAR=%~dp0scripts\ligar_jarvis.py"
if not exist "%JARVIS_PYW%" (
  echo  [ERRO] Rode o Iniciar-JARVIS.bat uma vez antes ^(ele prepara o Python do JARVIS^).
  pause
  exit /b 1
)
if not exist "%JARVIS_START%" (
  echo  [ERRO] Iniciar-JARVIS.bat nao encontrado nesta pasta.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$k='HKCU:\Software\Classes\jarvis'; New-Item -Path $k -Force | Out-Null; Set-Item -Path $k -Value 'URL:JARVIS'; New-ItemProperty -Path $k -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null; $c=New-Item -Path ($k + '\shell\open\command') -Force; Set-Item -Path ($k + '\shell\open\command') -Value ('\"' + $env:JARVIS_PYW + '\" \"' + $env:JARVIS_LIGAR + '\" --url \"%%1\"')"
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
