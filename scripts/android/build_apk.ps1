# Gera o app Android do JARVIS (V4.5) sem Gradle: aapt2 -> javac -> d8 -> zipalign -> apksigner.
# Ferramentas em %USERPROFILE%\.jarvis-android (JDK 17 + Android SDK 34). Saída: mobile\dist\JARVIS.apk
# Compila numa pasta só-ASCII porque as ferramentas do Android falham com caminhos como "Área de Trabalho".
param(
    [switch]$Quiet,
    [string]$JdkRoot,
    [string]$AndroidSdkRoot,
    [string]$WorkRoot,
    [string]$OutputDirectory,
    [string]$KeystorePath,
    [switch]$UseEnvironmentKeystorePassword
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Tools = Join-Path $env:USERPROFILE ".jarvis-android"
$Jdk = if ($JdkRoot) { $JdkRoot } else { Join-Path $Tools "jdk" }
$Sdk = if ($AndroidSdkRoot) { $AndroidSdkRoot } else { Join-Path $Tools "sdk" }
$Bt = Join-Path $Sdk "build-tools\34.0.0"
$AndroidJar = Join-Path $Sdk "platforms\android-34\android.jar"
$Work = if ($WorkRoot) { $WorkRoot } else { Join-Path $Tools "build" }
$Out = if ($OutputDirectory) { $OutputDirectory } else { Join-Path $Root "mobile\dist" }

foreach ($requiredPath in @("$Jdk\bin\javac.exe", "$Bt\aapt2.exe", "$Bt\d8.bat", "$Bt\zipalign.exe", "$Bt\apksigner.bat", $AndroidJar)) {
    if (-not (Test-Path $requiredPath)) { throw "Falta $requiredPath. Instale o JDK 17 e o Android SDK 34." }
}
if ($KeystorePath -and -not (Test-Path $KeystorePath)) {
    throw "O arquivo de keystore indicado não foi encontrado."
}
if ($UseEnvironmentKeystorePassword -and [string]::IsNullOrWhiteSpace($env:ANDROID_KEYSTORE_PASSWORD)) {
    throw "A variável de ambiente ANDROID_KEYSTORE_PASSWORD não foi definida."
}
$env:JAVA_HOME = $Jdk
$env:Path = "$Jdk\bin;$env:Path"

function Step($text) { if (-not $Quiet) { Write-Host "  $text" } }
function Run($exe, [string[]]$argv, [switch]$RedactArguments) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) {
        if ($RedactArguments) { throw "Falha na ferramenta de assinatura (código $LASTEXITCODE)." }
        throw "Falhou: $exe $($argv -join ' ')"
    }
}

# 1) Copia o código do app para a pasta de trabalho
if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }
New-Item -ItemType Directory -Force "$Work\app", "$Work\gen", "$Work\classes", "$Work\flat", "$Work\dex" | Out-Null
Copy-Item -Recurse (Join-Path $Root "mobile\android\*") "$Work\app"

# A versão do pacote vem do backend; somente o manifesto da pasta de trabalho é alterado.
$versionSource = Get-Content (Join-Path $Root "backend\version.py") -Raw
if ($versionSource -notmatch 'VERSION\s*=\s*["''](\d+)\.(\d+)\.(\d+)["'']') {
    throw "Não consegui ler VERSION em backend\version.py."
}
$versionName = "$($Matches[1]).$($Matches[2]).$($Matches[3])"
$versionCode = ([int]$Matches[1] * 10000) + ([int]$Matches[2] * 100) + [int]$Matches[3]
$manifestPath = Join-Path $Work "app\AndroidManifest.xml"
[xml]$manifest = Get-Content $manifestPath
$androidNamespace = "http://schemas.android.com/apk/res/android"
$previousVersionCode = [int]$manifest.manifest.GetAttribute("versionCode", $androidNamespace)
if ($versionCode -le $previousVersionCode) {
    throw "versionCode calculado ($versionCode) não é maior que o manifesto ($previousVersionCode)."
}
$null = $manifest.manifest.SetAttribute("versionCode", $androidNamespace, [string]$versionCode)
$null = $manifest.manifest.SetAttribute("versionName", $androidNamespace, $versionName)
$manifest.Save($manifestPath)

# 2) Ícones (a partir do avatar do branding) em todas as densidades
Step "[1/6] Gerando ícones..."
$avatar = Join-Path $Root "frontend\public\brand\avatar-512.png"
$sizes = @{ "mdpi" = 48; "hdpi" = 72; "xhdpi" = 96; "xxhdpi" = 144; "xxxhdpi" = 192 }
foreach ($d in $sizes.Keys) {
    $dir = "$Work\app\res\mipmap-$d"
    New-Item -ItemType Directory -Force $dir | Out-Null
    $px = $sizes[$d]
    & ffmpeg -nostdin -loglevel error -y -i $avatar -vf "scale=${px}:${px}:flags=lanczos" "$dir\ic_launcher.png"
    if ($LASTEXITCODE -ne 0) { throw "ffmpeg falhou ao gerar o ícone $d" }
}

# 3) Recursos + manifesto
Step "[2/6] Compilando recursos (aapt2)..."
Run "$Bt\aapt2.exe" @("compile", "--dir", "$Work\app\res", "-o", "$Work\flat\res.zip")
Run "$Bt\aapt2.exe" @("link", "-I", $AndroidJar, "--manifest", "$Work\app\AndroidManifest.xml",
    "-A", "$Work\app\assets", "--java", "$Work\gen", "--min-sdk-version", "24", "--target-sdk-version", "34",
    "-o", "$Work\base.apk", "$Work\flat\res.zip")

# 4) Java -> classes -> dex
Step "[3/6] Compilando o código (javac)..."
$sources = Get-ChildItem -Recurse "$Work\app\src", "$Work\gen" -Filter *.java | ForEach-Object { $_.FullName }
Run "$Jdk\bin\javac.exe" (@("-source", "1.8", "-target", "1.8", "-nowarn", "-Xlint:-options", "-encoding", "UTF-8",
    "-classpath", $AndroidJar, "-d", "$Work\classes") + $sources)
Step "[4/6] Convertendo para Android (d8)..."
$classFiles = Get-ChildItem -Recurse "$Work\classes" -Filter *.class | ForEach-Object { $_.FullName }
Run "$Bt\d8.bat" (@("--release", "--min-api", "24", "--lib", $AndroidJar, "--output", "$Work\dex") + $classFiles)

# 5) Junta o dex no APK e alinha
Step "[5/6] Montando o APK..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$Work\base.apk", "Update")
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$Work\dex\classes.dex", "classes.dex") | Out-Null
$zip.Dispose()
Run "$Bt\zipalign.exe" @("-f", "-p", "4", "$Work\base.apk", "$Work\aligned.apk")

# 6) Assina (a mesma chave sempre, para o celular aceitar atualizações por cima)
Step "[6/6] Assinando..."
$ks = if ($KeystorePath) { $KeystorePath } else { Join-Path $Tools "jarvis-release.jks" }
$passFile = Join-Path $Tools "jarvis-release-senha.txt"
if (-not (Test-Path $ks)) {
    if ($KeystorePath) { throw "O arquivo de keystore indicado não foi encontrado." }
    $pass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    Set-Content -Path $passFile -Value $pass -Encoding ascii -NoNewline
    Run "$Jdk\bin\keytool.exe" @("-genkeypair", "-keystore", $ks, "-alias", "jarvis", "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "10000", "-storepass", $pass, "-keypass", $pass, "-dname", "CN=JARVIS, O=Patrick Souza, C=BR") -RedactArguments
}
if ($UseEnvironmentKeystorePassword) {
    $pass = $env:ANDROID_KEYSTORE_PASSWORD
} else {
    if (-not (Test-Path $passFile)) { throw "Arquivo de senha do keystore não encontrado em $Tools." }
    $pass = (Get-Content $passFile -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($pass)) { throw "A senha do keystore está vazia." }
New-Item -ItemType Directory -Force $Out | Out-Null
Run "$Bt\apksigner.bat" @("sign", "--ks", $ks, "--ks-key-alias", "jarvis", "--ks-pass", "pass:$pass",
    "--out", "$Out\JARVIS.apk", "$Work\aligned.apk") -RedactArguments
Run "$Bt\apksigner.bat" @("verify", "$Out\JARVIS.apk")
Remove-Item -Force "$Out\JARVIS.apk.idsig" -ErrorAction SilentlyContinue

# V5.6: a versão do APK fica ao lado dele. O PC anuncia ESTA versão ao app (não a do JARVIS), então o
# celular só se atualiza quando o app em si mudou e foi gerado de novo.
Set-Content -Path "$Out\JARVIS.apk.version" -Value $versionName -Encoding ascii -NoNewline
$size = [math]::Round((Get-Item "$Out\JARVIS.apk").Length / 1KB)
Write-Host "  [OK] $Out\JARVIS.apk ($size KB)"
