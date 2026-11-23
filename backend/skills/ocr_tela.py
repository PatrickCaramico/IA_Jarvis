"""Ler texto da tela, OFFLINE (V9.0): o reconhecimento de texto (OCR) que já vem no Windows, sem internet nem IA.

Frases:
- "copia o texto da tela", "pega o texto da tela", "extrai o texto da tela", "o que está escrito na tela?"
- "copia o texto da imagem que eu copiei", "lê o texto do print que eu copiei" (imagem na área de transferência)
O texto reconhecido vai para a área de transferência (é só colar) e aparece num cartão. "Leia/explica a tela"
continua com a IA olhando a tela (modules/screen_assist.py); esta skill é para TIRAR o texto, na hora.
Usa Windows.Media.Ocr pelo PowerShell (idioma do Windows; o português vem no Windows em português).
Nada fica salvo: a imagem temporária é apagada logo depois.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.ocr_tela")

PS_TIMEOUT_S = 40
MAX_CHARS = 20000

# OCR de um arquivo de imagem (caminho em $env:JARVIS_IMG); escreve as linhas em UTF-8
OCR_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $type) { $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $null = $t.Wait(-1); $t.Result }
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) { Write-Output '##SEM_OCR##'; exit 0 }
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($env:JARVIS_IMG)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$stream.Dispose()
foreach ($line in $result.Lines) { Write-Output $line.Text }
"""

# imagem da área de transferência -> arquivo PNG em $env:JARVIS_IMG (precisa de -STA)
CLIP_IMAGE_SCRIPT = r"""
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$img = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $img) { Write-Output '##SEM_IMAGEM##'; exit 0 }
$img.Save($env:JARVIS_IMG, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output 'ok'
"""


def _ps(script: str, image: Path, sta: bool = False) -> str:
    """Roda um script do PowerShell sem janela, com o caminho da imagem por variável de ambiente (nada vira comando)."""
    args = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
    if sta:
        args.append("-STA")
    args += ["-Command", script]
    out = subprocess.run(args, env={**os.environ, "JARVIS_IMG": str(image)}, capture_output=True, timeout=PS_TIMEOUT_S,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or b"").decode("utf-8", "replace")[-400:] or f"PowerShell saiu com {out.returncode}")
    return (out.stdout or b"").decode("utf-8", "replace")


def capture_screen() -> Path:
    from modules import system_control

    return system_control._take_screenshot()


def clipboard_image() -> Optional[Path]:
    path = Path(tempfile.gettempdir()) / f"jarvis_ocr_clip_{os.getpid()}.png"
    return path if "##SEM_IMAGEM##" not in _ps(CLIP_IMAGE_SCRIPT, path, sta=True) and path.exists() else None


def ocr(image: Path) -> Optional[str]:
    """O texto da imagem (linhas), ou None se o Windows não tem o reconhecimento de texto instalado."""
    raw = _ps(OCR_SCRIPT, image)
    if "##SEM_OCR##" in raw:
        return None
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in raw.splitlines()]
    return "\n".join(ln for ln in lines if ln)[:MAX_CHARS]


_PATTERNS = [
    (re.compile(r"\b(?:copia|copie|pega|pegue|extrai|extraia|tira|tire|transcreve|transcreva|le|leia|ler)\s+(?:o\s+|todo o\s+)?texto\s+"
                r"(?:da|dessa|desta|na)\s+(?:tela|janela)\b"), "tela"),
    (re.compile(r"\bo que (?:esta|ta) escrito na tela\b"), "tela"),
    (re.compile(r"\b(?:copia|copie|pega|pegue|extrai|extraia|tira|tire|le|leia|ler|transcreve|transcreva)\s+(?:o\s+)?texto\s+"
                r"(?:da|dessa|desta|do|desse|deste)\s+(?:imagem|print|foto|captura)(?:\s+que eu copiei|\s+copiad[ao])?\b"), "imagem"),
]


def _parse(norm: str, _original: str) -> Optional[dict]:
    for rx, fonte in _PATTERNS:
        if rx.search(norm):
            return {"fonte": fonte}
    return None


@skill(
    name="ler_texto_da_tela",
    title="ler o texto da tela",
    description=("Reconhece o texto da tela inteira (fonte tela) ou de uma imagem que o usuário copiou (fonte imagem) "
                 "com o OCR do próprio Windows, offline, e põe o texto na área de transferência."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=60,
    parse=_parse,
    params={"type": "object", "required": ["fonte"], "properties": {
        "fonte": {"type": "string", "enum": ["tela", "imagem"]}}},
    examples=["copia o texto da tela", "copia o texto da imagem que eu copiei"],
)
def ler_texto_da_tela(ctx: SkillContext, fonte: str = "tela") -> SkillResult:
    if os.name != "nt":
        return SkillResult(ok=False, speech="Ler o texto da tela funciona no PC com Windows, senhor.")
    image: Optional[Path] = None
    try:
        image = clipboard_image() if fonte == "imagem" else capture_screen()
        if image is None:
            return SkillResult(ok=False, speech="Não tem imagem na área de transferência, senhor. Copie um print e peça de novo.")
        text = ocr(image)
    except (OSError, subprocess.SubprocessError, RuntimeError):
        log.exception("OCR do Windows falhou")
        return SkillResult(ok=False, speech="Não consegui ler o texto agora, senhor. O detalhe ficou no log.")
    finally:
        if image is not None:
            try:
                image.unlink()
            except OSError:
                log.debug("Não apaguei a imagem temporária %s", image)
    if text is None:
        return SkillResult(ok=False, speech="O reconhecimento de texto do Windows não está instalado, senhor. Ele vem com o pacote "
                                            "de idioma português, em Configurações do Windows, Hora e idioma.")
    if not text.strip():
        return SkillResult(speech="Não achei texto legível na " + ("imagem" if fonte == "imagem" else "tela") + ", senhor.")
    from skills.clipboard_ai import write_clipboard

    copied = write_clipboard(text)
    lines = text.splitlines()
    first = lines[0][:90]
    speech = (f"{'Copiei' if copied else 'Li'} {len(lines)} {'linha' if len(lines) == 1 else 'linhas'} de texto"
              f"{', é só colar' if copied else ''}. Começa com: {first}")
    rows = [{"label": str(i + 1), "value": ln[:160]} for i, ln in enumerate(lines[:12])]
    return SkillResult(speech=speech, data={"texto": text[:4000]},
                       cards=[{"type": "skill", "data": {"tag": "TEXTO DA " + ("IMAGEM" if fonte == "imagem" else "TELA"),
                                                         "source": f"{len(lines)} linhas · OCR do Windows, offline", "rows": rows}}])
