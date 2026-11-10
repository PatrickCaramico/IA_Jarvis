$backendUrl = "http://127.0.0.1:8000/api/health"
$frontPort = 5173
$frontOnline = $false

try {
    $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $frontPort)
    $frontOnline = $true
    $tcp.Close()
} catch {
    $frontOnline = $false
}

try {
    $resp = Invoke-RestMethod -Uri $backendUrl -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  [OK] Backend:          NO AR" -ForegroundColor Green
    if ($frontOnline) {
        Write-Host "  [OK] Frontend:         NO AR (http://127.0.0.1:5173)" -ForegroundColor Green
    } else {
        Write-Host "  [AVISO] Frontend:      FORA DO AR" -ForegroundColor Yellow
    }
    
    $versao = $resp.version
    $provider = ("" + $resp.provider).ToUpper()
    $personalidade = $resp.personality
    $timers = $resp.timers
    $perfilStr = "Nao cadastrado"
    if ($resp.has_profile) {
        $perfilStr = "Sim (Cadastrado)"
    }
    $statusSistema = "Pronto para uso"
    if ($resp.busy) {
        $statusSistema = "Ocupado / Processando"
    }

    Write-Host ("  Versao:                " + $versao)
    Write-Host ("  Provedor de IA:        " + $provider)
    Write-Host ("  Personalidade:         " + $personalidade)
    Write-Host ("  Timers Ativos:         " + $timers)
    Write-Host ("  Perfil Facial:         " + $perfilStr)
    Write-Host ("  Status do Sistema:     " + $statusSistema)
} catch {
    Write-Host "  [!] Backend:           FORA DO AR" -ForegroundColor Red
    if ($frontOnline) {
        Write-Host "  [OK] Frontend:         NO AR (http://127.0.0.1:5173)" -ForegroundColor Yellow
    } else {
        Write-Host "  [!] Frontend:          FORA DO AR" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  O JARVIS parece estar desligado no momento." -ForegroundColor Yellow
    Write-Host "  -> Para iniciar normalmente: execute Iniciar-JARVIS.bat ou Abrir-Painel.bat"
    Write-Host "  -> Se houver algum erro de inicializacao: execute Diagnostico-Backend.bat"
}
