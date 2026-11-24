"""Analisar imagem por voz (V9.4): "analisa essa imagem", "o que tem nessa foto?", "analisa o print que eu tirei".

Antes: a análise de foto só existia arrastando a imagem para a central (ou pelo 📎 / galeria do celular). Pedir por voz
caía na IA sem imagem nenhuma, e ela inventava ou pedia a foto. Agora o JARVIS procura a imagem sozinho, nesta ordem:
  1. a imagem copiada (Ctrl+C numa imagem, Win+Shift+S ou um arquivo de imagem copiado no Explorer);
  2. a imagem mais nova (últimos 30 minutos) em Downloads, Área de Trabalho, Imagens ou na pasta de capturas de tela;
e manda para a IA de visão junto com a pergunta. Sem imagem, diz como fazer. A imagem não é guardada em lugar nenhum
(só a miniatura vai para a IA, como no 📎). Na central, Ctrl+V com uma imagem também abre a análise (PhotoPanel).
"""
from __future__ import annotations

import base64
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.analisar_imagem")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
RECENT_S = 30 * 60
MAX_WIDTH = 1280
MAX_BYTES = 25 * 1024 * 1024

_NOUN = r"(?:imagem|imagens|foto|fotografia|print|printscreen|captura(?: de tela)?|screenshot|figura)"
_PATTERNS = [
    re.compile(rf"\b(?:analisa|analise|analisar|descreve|descreva|examina|examine|le|leia|explica|explique|olha|olhe|ve|veja)\s+"
               rf"(?:pra mim\s+)?(?:essa|esta|a|minha|aquela|o|este|esse|meu|ultima|ultimo|a ultima|o ultimo)?\s*(?:ultima\s+|ultimo\s+)?"
               rf"{_NOUN}\b"),
    re.compile(rf"\bo que (?:tem|aparece|esta escrito|diz|mostra)\s+(?:nessa|nesta|na|neste|nesse|no)\s+{_NOUN}\b"),
    re.compile(rf"\bo que (?:e|significa) (?:essa|esta|a) {_NOUN}\b"),
    re.compile(rf"\b{_NOUN} que eu (?:copiei|baixei|salvei|tirei)\b"),
]


def _parse(norm: str, _original: str) -> Optional[dict]:
    # "a câmera"/"a tela" têm caminhos próprios (janela da câmera e leitura de tela)
    # "o texto da imagem" é do OCR (skills/ocr_tela.py: copia o texto, sem IA)
    if re.search(r"\b(?:camera|webcam|texto)\b", norm):
        return None
    return {} if any(rx.search(norm) for rx in _PATTERNS) else None


# ------------------------------------------------------------------ onde achar a imagem
def _folders() -> list[Path]:
    home = Path.home()
    names = ["Downloads", "Desktop", "Área de Trabalho", "Pictures", "Imagens", "Pictures/Screenshots",
             "Imagens/Capturas de Tela", "Pictures/Capturas de tela", "OneDrive/Imagens/Capturas de Tela",
             "OneDrive/Pictures/Screenshots", "OneDrive/Área de Trabalho", "OneDrive/Desktop", "Videos/Captures"]
    return [home / n for n in names]


def newest_image(folders: Optional[list[Path]] = None, now: Optional[float] = None, max_age: float = RECENT_S) -> Optional[Path]:
    """A imagem mais nova (até `max_age` segundos) nas pastas, sem entrar em subpastas."""
    now = time.time() if now is None else now
    best: tuple[float, Optional[Path]] = (0.0, None)
    for folder in folders if folders is not None else _folders():
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for e in entries:
            if not e.is_file() or Path(e.name).suffix.lower() not in IMAGE_EXT:
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            if now - st.st_mtime <= max_age and st.st_size <= MAX_BYTES and st.st_mtime > best[0]:
                best = (st.st_mtime, Path(e.path))
    return best[1]


def clipboard_image() -> tuple[Optional[bytes], str]:
    """(bytes da imagem copiada, de onde veio) ou (None, "")."""
    try:  # Pillow (quando instalado) lê a imagem e também o arquivo de imagem copiado no Explorer
        from PIL import ImageGrab

        got = ImageGrab.grabclipboard()
        if isinstance(got, list):
            for p in got:
                path = Path(p)
                if path.suffix.lower() in IMAGE_EXT and path.is_file() and path.stat().st_size <= MAX_BYTES:
                    return path.read_bytes(), f"o arquivo copiado {path.name}"
        elif got is not None:
            import io

            buf = io.BytesIO()
            got.convert("RGB").save(buf, "JPEG", quality=90)
            return buf.getvalue(), "a imagem copiada"
    except Exception:  # noqa: BLE001 - sem Pillow ou fora do Windows: tenta o PowerShell
        log.debug("Pillow não leu a área de transferência", exc_info=True)
    if os.name != "nt":
        return None, ""
    from skills import ocr_tela  # o mesmo leitor da área de transferência do "copia o texto da imagem"

    try:
        path = ocr_tela.clipboard_image()
    except Exception:  # noqa: BLE001
        log.warning("Não consegui ler a área de transferência", exc_info=True)
        return None, ""
    if not path:
        return None, ""
    try:
        return path.read_bytes(), "a imagem copiada"
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def find_image() -> tuple[Optional[bytes], str]:
    data, src = clipboard_image()
    if data:
        return data, src
    path = newest_image()
    if path:
        try:
            return path.read_bytes(), f"a imagem {path.name}"
        except OSError:
            log.warning("Não consegui ler %s", path, exc_info=True)
    return None, ""


def to_jpeg_b64(data: bytes) -> str:
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("A imagem não abriu.")
    h, w = img.shape[:2]
    if w > MAX_WIDTH:
        img = cv2.resize(img, (MAX_WIDTH, int(h * MAX_WIDTH / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise ValueError("A imagem não abriu.")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def build_prompt(question: str, source: str) -> str:
    return (
        f"A imagem anexada é {source} do computador do usuário, enviada agora a pedido dele (não é a câmera). "
        "Responda em português do Brasil. Se ele só pediu para analisar, diga o que é, os detalhes importantes e uma "
        "dica útil; se perguntou algo, responda à pergunta. Comece com a resposta em uma ou duas frases curtas, sem "
        "markdown. Se algo não estiver legível, diga isso em vez de adivinhar. Não repita senhas, números de cartão "
        "ou códigos que apareçam.\n"
        f'Pedido do usuário: "{question}"'
    )


def short_speech(text: str, limit: int = 2) -> str:
    clean = re.sub(r"[*_#`>]+", "", text or "").strip()
    parts = re.split(r"(?<=[.!?])\s+", clean)
    return " ".join(parts[:limit]).strip()


@skill(
    name="analisar_imagem",
    title="analisar a imagem",
    description=("Analisa uma imagem do PC: a que o usuário copiou (Ctrl+C, Win+Shift+S) ou a mais nova salva nos "
                 "últimos 30 minutos (Downloads, Área de Trabalho, capturas de tela) e responde ao pedido sobre ela."),
    permission=Permission.READ,
    timeout=45,
    llm=False,  # usa a IA de visão por conta própria (e pode passar do prazo de um turno da IA)
    allow_remote=False,  # a imagem está no PC; do celular, use o 📎 da central
    parse=_parse,
    params={"type": "object", "properties": {}},
    examples=["analisa essa imagem", "o que tem nessa foto?", "analisa o print que eu tirei"],
)
async def analisar_imagem(ctx: SkillContext) -> SkillResult:
    import asyncio

    from services import llm_orchestrator

    data, source = await asyncio.to_thread(find_image)
    if not data:
        return SkillResult(ok=False, speech="Não achei nenhuma imagem, senhor. Copie a imagem com Control C, ou tire "
                                            "um print com Windows Shift S, e me peça de novo. Também dá para arrastar "
                                            "a imagem para a central.")
    try:
        image = await asyncio.to_thread(to_jpeg_b64, data)
    except Exception:  # noqa: BLE001
        log.exception("Imagem para analisar não abriu (%s)", source)
        return SkillResult(ok=False, speech="Achei a imagem, mas não consegui abri-la, senhor. Tente copiar de novo.")
    await ctx.broadcast({"type": "agent", "agent": "imagem", "label": "Analisando a imagem", "icon": "🖼",
                         "status": "working", "text": f"Olhando {source}…"})
    try:
        answer = await asyncio.to_thread(llm_orchestrator.ask_with_image, build_prompt(ctx.message, source), image)
    except Exception:  # noqa: BLE001
        log.exception("A IA não respondeu sobre a imagem")
        await ctx.broadcast({"type": "agent", "agent": "imagem", "label": "Analisando a imagem", "icon": "🖼",
                             "status": "error", "text": "A IA não respondeu."})
        return SkillResult(ok=False, speech="Peguei a imagem, mas a IA não respondeu agora, senhor. Tente de novo em instantes.")
    answer = (answer or "").strip()
    await ctx.broadcast({"type": "agent", "agent": "imagem", "label": "Analisando a imagem", "icon": "🖼",
                         "status": "done", "text": "Pronto."})
    if not answer:
        return SkillResult(speech="Olhei a imagem, mas não encontrei nada para comentar, senhor.")
    return SkillResult(
        speech=short_speech(answer) or "Pronto, senhor. A análise está na tela.",
        cards=[{"type": "skill", "data": {"tag": "ANÁLISE DA IMAGEM", "source": source,
                                          "rows": [{"label": "O que vi", "value": answer[:1500]}]}}],
    )
