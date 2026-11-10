@echo off
title J.A.R.V.I.S. - Remover botao LIGAR O JARVIS do site
color 0C
rem Apaga o atalho jarvis:// criado pelo Instalar-Botao-Ligar.bat (so do seu usuario).
powershell -NoProfile -Command "Remove-Item -Path 'HKCU:\Software\Classes\jarvis' -Recurse -Force -ErrorAction SilentlyContinue"
echo  [OK] Botao LIGAR O JARVIS desativado. O site volta a pedir para ligar pelo Iniciar-JARVIS.bat.
pause
exit /b 0
