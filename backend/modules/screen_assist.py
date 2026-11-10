"""Consciência de tela (4.2, funcionalidade 1 do backlog).

"Jarvis, o que é esse erro na tela?" captura a tela, reduz a imagem e manda para a IA junto com a
pergunta. A captura existe só em memória durante a pergunta: o arquivo temporário do print é
apagado na hora e nada é guardado. Só funciona com a central liberada (o modo bloqueado e o
visitante nunca chegam aqui) e pode ser desligado em Configurações > Automação.
"""
from __future__ import annotations

import base64
import logging
import re
from typing import Optional

log = logging.getLogger("jarvis.screen")

MAX_WIDTH = 1600
JPEG_QUALITY = 80

# Pede algo sobre o que está na tela (não confundir com "tira um print", que só salva a imagem).
_CONTEXT_RE = re.compile(r"\b(?:na|da|nessa|nesta|dessa|desta|minha|essa|esta)\s+(?:tela|janela)\b")
_ASK_RE = re.compile(
    r"\b(?:o que|oque|qual|quais|como|por que|porque|leia|le|ler|analisa|analise|explica|explique|olha|olhe|"
    r"veja|ve|traduz|traduza|resume|resuma|resolve|resolva|ajuda|significa)\b"
)
_COMMAND_RE = re.compile(
    r"\b(?:leia|le|ler|analisa|analise|explica|explique|olha|olhe|veja|traduz|traduza|resume|resuma)\s+"
    r"(?:a\s+|minha\s+|essa\s+|esta\s+)?(?:tela|janela)\b"
)
_EXCLUDE_RE = re.compile(r"\b(?:print|screenshot|captura de tela|bloque\w*|brilho|tela cheia|desliga\w*)\b")


def wants_screen(norm: str) -> bool:
    """`norm` já normalizado (sem acentos, minúsculo, pontuação vira espaço)."""
    if _EXCLUDE_RE.search(norm):
        return False
    return bool(_COMMAND_RE.search(norm) or (_CONTEXT_RE.search(norm) and _ASK_RE.search(norm)))


def capture_jpeg_b64() -> str:
    """Captura a tela inteira e devolve um JPEG reduzido em base64 (nada fica salvo em disco)."""
    import cv2
    import numpy as np

    from modules import system_control

    path = system_control._take_screenshot()
    try:
        data = np.frombuffer(path.read_bytes(), np.uint8)
    finally:
        try:
            path.unlink()
        except OSError:
            log.debug("Não foi possível apagar o print temporário %s", path)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("A captura de tela veio vazia.")
    h, w = img.shape[:2]
    if w > MAX_WIDTH:
        img = cv2.resize(img, (MAX_WIDTH, int(h * MAX_WIDTH / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError("Não consegui preparar a imagem da tela.")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def build_prompt(question: str) -> str:
    return (
        "A imagem anexada é uma captura da TELA do computador do usuário, feita agora a pedido dele "
        "(não é a câmera). Responda à pergunta com base no que aparece na tela. Se for um erro, diga "
        "em poucas frases o que significa e o primeiro passo para resolver. Se não der para ler algo, "
        "diga isso em vez de adivinhar. Não repita dados sensíveis que estejam visíveis "
        "(senhas, números de cartão, códigos).\n"
        f'Pergunta do usuário: "{question}"'
    )


async def answer(question: str) -> Optional[str]:
    """Captura a tela e pergunta à IA. Devolve a resposta falada (ou um aviso se algo falhar)."""
    import asyncio

    from modules import prefs
    from services import llm_orchestrator

    if not prefs.get_all().get("screen_assist_enabled", True):
        return "A leitura de tela está desligada, senhor. Dá para ligar em Configurações, na aba Automação."
    try:
        image = await asyncio.to_thread(capture_jpeg_b64)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao capturar a tela: %s", exc)
        return "Não consegui capturar a tela agora, senhor."
    try:
        text = await asyncio.to_thread(llm_orchestrator.ask_with_image, build_prompt(question), image)
    except Exception as exc:  # noqa: BLE001
        log.warning("IA não respondeu sobre a tela: %s", exc)
        return "Capturei a tela, mas a IA não respondeu agora, senhor. Tente de novo em instantes."
    return text or "Olhei a tela, mas não encontrei nada para comentar, senhor."
