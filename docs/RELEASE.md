# Publicar uma versão Android

A workflow `.github/workflows/release-apk.yml` gera e publica o APK ao receber uma tag `v*`. Ela usa a mesma keystore local para que o Android aceite a atualização por cima da versão instalada.

## Cadastrar os secrets

1. No GitHub, abra o repositório e vá a **Settings > Secrets and variables > Actions**.
2. Escolha **New repository secret** e crie `ANDROID_KEYSTORE_BASE64`.
3. No PowerShell do seu PC, copie a keystore em Base64 para a área de transferência, sem mostrar o conteúdo no terminal:

   ```powershell
   $keystore = Join-Path $env:USERPROFILE ".jarvis-android\jarvis-release.jks"
   [Convert]::ToBase64String([IO.File]::ReadAllBytes($keystore)) | Set-Clipboard
   ```

4. Cole o conteúdo no campo do secret `ANDROID_KEYSTORE_BASE64` e salve.
5. Crie outro repository secret chamado `ANDROID_KEYSTORE_PASSWORD`. Abra localmente `%USERPROFILE%\.jarvis-android\jarvis-release-senha.txt` e cole a senha diretamente no formulário do GitHub. Não a coloque em arquivos do repositório nem em logs.

A keystore e a senha devem ser as mesmas usadas para assinar o app instalado. Não regenere a keystore para uma atualização existente.

## Publicar

1. Atualize `VERSION` em `backend/version.py` e crie a seção correspondente no `CHANGELOG.md`.
2. Confirme que o valor da versão corresponde à tag, por exemplo `VERSION = "5.0.0"` e tag `v5.0.0`.
3. Envie a tag para o GitHub:

   ```powershell
   git tag v5.0.0
   git push origin v5.0.0
   ```

4. Em **Actions**, acompanhe **Release Android APK**. A workflow instala JDK 17, Android SDK 34, Build Tools 34.0.0 e FFmpeg; compila, assina com a keystore dos secrets e anexa `JARVIS-5.0.0.apk` à release.
5. A seção da versão no `CHANGELOG.md` é usada como notas da release. Se ela não existir ou estiver vazia, a workflow para antes de assinar ou publicar.

A chave é materializada apenas na pasta temporária do runner e removida ao final do job. O APK assinado é publicado na release; nenhum secret é salvo no repositório ou impresso nos logs.
