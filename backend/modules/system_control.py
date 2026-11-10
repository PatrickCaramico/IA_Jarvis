"""Controle do sistema operacional: volume, brilho, silenciar, bloquear tela e print.

Todas as operações são específicas para Windows (usando ctypes, nircmd ou PowerShell).
"""
import asyncio
import logging
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("jarvis.system")


# ===================================================================== volume
def _pycaw_endpoint():
    from pycaw.pycaw import AudioUtilities

    speakers = AudioUtilities.GetSpeakers()
    # pycaw exposes EndpointVolume directly in recent releases.
    if hasattr(speakers, "EndpointVolume"):
        return speakers.EndpointVolume
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def _run_ps(script: str) -> str:
    """Executa um trecho de PowerShell e devolve stdout."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def _set_volume(level: int) -> None:
    """Define o volume master do Windows (0‑100)."""
    level = max(0, min(100, level))
    try:
        _pycaw_endpoint().SetMasterVolumeLevelScalar(level / 100, None)
        return
    except (ImportError, OSError, AttributeError, TypeError):
        log.debug("pycaw indisponível; usando fallback PowerShell.", exc_info=True)
    script = f"""
$obj = New-Object -ComObject WScript.Shell
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{ void _VtblGap1_6(); void SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext); }}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{ void _VtblGap1_4(); [return: MarshalAs(UnmanagedType.IUnknown)] object Activate(ref System.Guid iid, int dwClsCtx, System.IntPtr pActivationParams); }}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{ void _VtblGap1_1(); IMMDevice GetDefaultAudioEndpoint(int dataFlow, int role); }}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator {{}}
'@
$enum = [Activator]::CreateInstance([Type]::GetTypeFromCLSID([Guid]'BCDE0395-E52F-467C-8E3D-C4579291692E'))
$dev  = [IMMDeviceEnumerator].GetMethod('GetDefaultAudioEndpoint').Invoke($enum, @(0,1))
$iid  = [Guid]'5CDF2C82-841E-4546-9722-0CF74078229A'
$vol  = $dev.Activate([ref]$iid, 23, [IntPtr]::Zero)
[IAudioEndpointVolume].GetMethod('SetMasterVolumeLevelScalar').Invoke($vol, @([float]({level}/100.0), [Guid]::Empty))
""".strip()
    _run_ps(script)


def _get_volume() -> int:
    """Retorna o volume master atual (0‑100)."""
    try:
        return round(_pycaw_endpoint().GetMasterVolumeLevelScalar() * 100)
    except (ImportError, OSError, AttributeError, TypeError):
        log.debug("pycaw indisponível; usando fallback PowerShell.", exc_info=True)
    script = """
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume { void _VtblGap1_6(); void SetMasterVolumeLevelScalar(float f, System.Guid g); [return: MarshalAs(UnmanagedType.R4)] float GetMasterVolumeLevelScalar(); }
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice { void _VtblGap1_4(); [return: MarshalAs(UnmanagedType.IUnknown)] object Activate(ref System.Guid iid, int dwClsCtx, System.IntPtr p); }
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator { void _VtblGap1_1(); IMMDevice GetDefaultAudioEndpoint(int d, int r); }
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator {}
'@
$enum = [Activator]::CreateInstance([Type]::GetTypeFromCLSID([Guid]'BCDE0395-E52F-467C-8E3D-C4579291692E'))
$dev  = [IMMDeviceEnumerator].GetMethod('GetDefaultAudioEndpoint').Invoke($enum, @(0,1))
$iid  = [Guid]'5CDF2C82-841E-4546-9722-0CF74078229A'
$vol  = $dev.Activate([ref]$iid, 23, [IntPtr]::Zero)
[math]::Round([IAudioEndpointVolume].GetMethod('GetMasterVolumeLevelScalar').Invoke($vol, @()) * 100)
"""
    try:
        out = _run_ps(script)
        return int(out)
    except Exception:  # noqa: BLE001
        return -1


def _set_mute(mute: bool) -> None:
    state = "1" if mute else "0"
    script = f"""
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{ void _VtblGap1_6(); void SetMasterVolumeLevelScalar(float f, System.Guid g); void _VtblGap3_1(); void SetMute(bool b, System.Guid g); }}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{ void _VtblGap1_4(); [return: MarshalAs(UnmanagedType.IUnknown)] object Activate(ref System.Guid iid, int dwClsCtx, System.IntPtr p); }}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{ void _VtblGap1_1(); IMMDevice GetDefaultAudioEndpoint(int d, int r); }}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator {{}}
'@
$enum = [Activator]::CreateInstance([Type]::GetTypeFromCLSID([Guid]'BCDE0395-E52F-467C-8E3D-C4579291692E'))
$dev  = [IMMDeviceEnumerator].GetMethod('GetDefaultAudioEndpoint').Invoke($enum, @(0,1))
$iid  = [Guid]'5CDF2C82-841E-4546-9722-0CF74078229A'
$vol  = $dev.Activate([ref]$iid, 23, [IntPtr]::Zero)
[IAudioEndpointVolume].GetMethod('SetMute').Invoke($vol, @([bool]{state}, [Guid]::Empty))
"""
    _run_ps(script)


# ===================================================================== brilho (WMI)
def _set_brightness(level: int) -> bool:
    level = max(0, min(100, level))
    script = f"""
$m = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue
if ($m) {{ $m.WmiSetBrightness(1, {level}); Write-Output 'ok' }} else {{ Write-Output 'no_wmi' }}
"""
    out = _run_ps(script)
    return "ok" in out


def _get_brightness() -> int:
    script = """
$b = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue
if ($b) { $b.CurrentBrightness } else { -1 }
"""
    try:
        return int(_run_ps(script))
    except Exception:  # noqa: BLE001
        return -1


# ===================================================================== tela e print
def _lock_screen() -> None:
    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])


def _take_screenshot() -> Path:
    """Captura a tela e salva como PNG em %TEMP%. Devolve o caminho."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(tempfile.gettempdir()) / f"jarvis_print_{ts}.png"
    script = f"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('{out}')
$g.Dispose(); $bmp.Dispose()
"""
    _run_ps(script)
    return out


# ===================================================================== handlers de voz
_VOLUME_RE = re.compile(
    r"\b(?:volume|som)\b.*?\b(\d{1,3})\s*%?|"
    r"\b(\d{1,3})\s*%?\s*(?:de volume|no volume)\b"
)
_VOL_WORDS = {
    "aumente": +20, "aumenta": +20, "sobe": +20, "subir": +20, "subiu": +20,
    "diminua": -20, "diminui": -20, "baixa": -20, "baixar": -20, "abaixa": -20,
    "max": 100, "maximo": 100, "full": 100,
    "min": 10, "minimo": 10, "mute": 0, "silencia": 0, "silenciar": 0,
    "mudo": 0, "silencioso": 0, "sem som": 0,
}
_BRIGHT_RE = re.compile(
    r"\b(?:brilho|luminosidade)\b.*?\b(\d{1,3})\s*%?|"
    r"\b(\d{1,3})\s*%?\s*(?:de brilho|no brilho)\b"
)

# Estado anterior do sistema para permitir restauração (modo normal).
# "active" indica se algum modo especial (cinema/trabalho) foi ativado desde o último reset.
# Só é sobrescrito na primeira ativação; ativações subsequentes preservam os valores originais.
_previous_state: dict = {"volume": None, "brightness": None, "active": False}


def _save_current_state() -> None:
    """Guarda o volume e brilho originais antes de ativar um modo especial.

    Se já houver um modo especial ativo (_previous_state["active"] == True),
    não sobrescreve — os valores do usuário antes de qualquer modo são mantidos.
    """
    if _previous_state["active"]:
        # Já há um snapshot original; não sobrescrever (ex.: cinema -> trabalho).
        return
    vol = _get_volume()
    bri = _get_brightness()
    _previous_state["volume"] = vol if vol >= 0 else None
    _previous_state["brightness"] = bri if bri >= 0 else None
    _previous_state["active"] = True


async def handle(message: str, norm: str, words: int, name: str) -> Optional[str]:
    """Tenta executar um comando de controle do sistema. Devolve texto de confirmação ou None."""

    # ----- volume / mute -----
    is_volume = any(w in norm for w in ("volume", "som", "audio", "silencia", "mute", "mudo"))
    if is_volume:
        # silenciar / dessilenciar
        if any(w in norm for w in ("silencia", "mute", "mudo", "sem som", "silencioso")):
            await asyncio.to_thread(_set_mute, True)
            return "Silenciado."
        if re.search(r"\b(dessilencia|desmute|reativa|ativa o som|volta o som|aumentar)\b", norm):
            await asyncio.to_thread(_set_mute, False)
            return "Som reativado."
        # valor numérico explícito
        m = _VOLUME_RE.search(norm)
        if m:
            level = int(m.group(1) or m.group(2))
            await asyncio.to_thread(_set_volume, level)
            return f"Volume ajustado para {level}%."
        # palavras como "aumenta", "baixa"
        for word, delta in _VOL_WORDS.items():
            if word in norm:
                if delta in (0, 100, 10):
                    await asyncio.to_thread(_set_volume, delta)
                    return f"Volume ajustado para {delta}%."
                cur = await asyncio.to_thread(_get_volume)
                new = max(0, min(100, (cur if cur >= 0 else 50) + delta))
                await asyncio.to_thread(_set_volume, new)
                return f"Volume {'aumentado' if delta > 0 else 'diminuído'} para {new}%."

    # ----- brilho -----
    is_bright = any(w in norm for w in ("brilho", "luminosidade", "tela mais clara", "tela mais escura"))
    if is_bright:
        m = _BRIGHT_RE.search(norm)
        if m:
            level = int(m.group(1) or m.group(2))
            ok = await asyncio.to_thread(_set_brightness, level)
            if ok:
                return f"Brilho ajustado para {level}%."
            return "Não consegui ajustar o brilho. Pode ser que seu monitor não suporte controle por software."
        if any(w in norm for w in ("aumenta", "sobe", "mais claro", "mais clara", "aumente")):
            cur = await asyncio.to_thread(_get_brightness)
            new = min(100, (cur if cur >= 0 else 50) + 20)
            ok = await asyncio.to_thread(_set_brightness, new)
            return f"Brilho aumentado para {new}%." if ok else "Não consegui ajustar o brilho."
        if any(w in norm for w in ("diminui", "baixa", "mais escuro", "mais escura", "diminua")):
            cur = await asyncio.to_thread(_get_brightness)
            new = max(0, (cur if cur >= 0 else 50) - 20)
            ok = await asyncio.to_thread(_set_brightness, new)
            return f"Brilho reduzido para {new}%." if ok else "Não consegui ajustar o brilho."

    # ----- bloquear tela -----
    if re.search(r"\b(bloquei|bloquear|bloqueie|trava|travar|travando|lock)\b", norm) and \
       re.search(r"\b(tela|computador|pc|sessao|sessão|screen)\b", norm):
        await asyncio.to_thread(_lock_screen)
        return "Tela bloqueada."

    # ----- print / screenshot -----
    if re.search(r"\b(print|screenshot|captura de tela|printscreen|tire uma foto da tela|foto da tela)\b", norm):
        try:
            path = await asyncio.to_thread(_take_screenshot)
            return f"Print salvo em {path}."
        except Exception as exc:  # noqa: BLE001
            log.exception("Falha ao tirar print")
            return f"Não consegui tirar o print: {exc}"

    # ----- modo cinema / relaxar (Lazer & Produtividade) -----
    if any(k in norm for k in ("modo cinema", "modo filme", "hora do filme", "assistir filme")):
        await asyncio.to_thread(_save_current_state)
        # Baixa o volume para nível confortável, reduz brilho e abre central de entretenimento
        await asyncio.to_thread(_set_volume, 45)
        await asyncio.to_thread(_set_brightness, 35)
        return "Modo cinema ativado, senhor: volume e brilho ajustados. Bom filme."

    # ----- modo trabalho / foco total -----
    if any(k in norm for k in ("modo trabalho", "foco total", "hora de focar", "modo produtivo")):
        await asyncio.to_thread(_save_current_state)
        await asyncio.to_thread(_set_volume, 30)
        await asyncio.to_thread(_set_brightness, 85)
        return "Modo foco total engajado, senhor. Iluminação elevada para concentração e áudio equilibrado. Produtividade máxima."

    # ----- modo normal / sair do modo / voltar ao normal -----
    if any(k in norm for k in (
        "modo normal", "modo padrao", "modo padrão",
        "voltar ao normal", "sair do modo", "desfazer modo", "restaurar modo",
    )):
        # Nenhum modo especial foi ativado nesta sessão: nada para restaurar.
        if not _previous_state["active"]:
            return (
                "Não há nenhum modo especial ativo para restaurar, senhor. "
                "Volume e brilho permanecem como estão."
            )

        saved_vol = _previous_state["volume"]
        saved_bri = _previous_state["brightness"]
        detalhes: list[str] = []
        avisos: list[str] = []

        # Restaura volume se havia sido salvo.
        if saved_vol is not None:
            await asyncio.to_thread(_set_volume, saved_vol)
            detalhes.append(f"volume em {saved_vol}%")

        # Restaura brilho se havia sido salvo (brilho disponível na entrada do modo).
        if saved_bri is not None:
            ok = await asyncio.to_thread(_set_brightness, saved_bri)
            if ok:
                detalhes.append(f"brilho em {saved_bri}%")
            else:
                avisos.append("não foi possível restaurar o brilho neste monitor")
        else:
            # Brilho não foi salvo porque era -1 (monitor sem suporte) na entrada do modo.
            avisos.append("brilho não restaurado — controle não disponível neste monitor")

        # Zera o snapshot para que a próxima ativação de modo capture o estado atual.
        _previous_state["volume"] = None
        _previous_state["brightness"] = None
        _previous_state["active"] = False

        detalhes_str = (" (" + " e ".join(detalhes) + ")") if detalhes else ""
        avisos_str = (". Aviso: " + "; ".join(avisos)) if avisos else ""
        return f"Modo normal restaurado, senhor{detalhes_str}{avisos_str}."

    return None
