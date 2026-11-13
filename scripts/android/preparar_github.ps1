# V6.7.7: entrega ao GitHub a MESMA chave que assina o app no PC, para o GitHub gerar o APK sozinho a cada
# versão nova e o celular se atualizar de qualquer lugar (o Android só aceita atualização com a mesma chave).
# Nada é enviado por este script: ele abre a página dos "secrets" do repositório e põe cada valor na área de
# transferência para você colar. No fim, limpa a área de transferência.
$ErrorActionPreference = "Stop"
$Tools = Join-Path $env:USERPROFILE ".jarvis-android"
$ks = Join-Path $Tools "jarvis-release.jks"
$passFile = Join-Path $Tools "jarvis-release-senha.txt"
$repo = "https://github.com/PatrickCaramico/IA_Jarvis"

if (-not (Test-Path $ks) -or -not (Test-Path $passFile)) {
    Write-Host " Ainda nao existe a chave do app neste PC." -ForegroundColor Yellow
    Write-Host " Gere o app uma vez com o Gerar-App-Android.bat e rode este de novo."
    exit 1
}

Write-Host " Este passo e feito UMA vez. Ele NAO envia nada sozinho:" -ForegroundColor Cyan
Write-Host " abre a pagina do GitHub e coloca cada valor na area de transferencia para voce colar."
Write-Host " Nao compartilhe esses valores com ninguem."
Write-Host ""
Read-Host " Pressione ENTER para abrir o GitHub (entre na sua conta se pedir)"
Start-Process "$repo/settings/secrets/actions/new"

Set-Clipboard -Value ([Convert]::ToBase64String([IO.File]::ReadAllBytes($ks)))
Write-Host ""
Write-Host " 1/2  A CHAVE do app esta copiada." -ForegroundColor Green
Write-Host "      No GitHub, em Name escreva:   ANDROID_KEYSTORE_BASE64"
Write-Host "      Em Secret, cole (Ctrl+V) e toque em Add secret."
Read-Host " Pressione ENTER quando terminar"

Start-Process "$repo/settings/secrets/actions/new"
Set-Clipboard -Value ((Get-Content $passFile -Raw).Trim())
Write-Host ""
Write-Host " 2/2  A SENHA da chave esta copiada." -ForegroundColor Green
Write-Host "      Em Name escreva:   ANDROID_KEYSTORE_PASSWORD"
Write-Host "      Em Secret, cole (Ctrl+V) e toque em Add secret."
Read-Host " Pressione ENTER quando terminar"

Set-Clipboard -Value " "
Write-Host ""
Write-Host " Pronto. Agora vou abrir a pagina que gera o APK no GitHub:" -ForegroundColor Cyan
Write-Host " toque em 'Run workflow' (botao a direita) e confirme. Leva uns 5 minutos."
Write-Host " Depois disso, a cada versao nova o GitHub gera o APK sozinho, e o app se atualiza de qualquer lugar."
Start-Process "$repo/actions/workflows/release-apk.yml"
