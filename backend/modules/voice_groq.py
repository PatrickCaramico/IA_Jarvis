"""V8.4.0 (ideia 10): a voz entendida pela Groq (Whisper), para a ilha e o app do Windows.

Dentro do app do Windows o reconhecimento de voz do navegador não funciona bem; ali o 🎙 grava o áudio e
manda para cá, e a Groq transcreve (grátis, com a mesma chave do Cérebro). O áudio não é guardado: vai da
memória direto para a Groq e o texto volta para a ilha/app, que manda ao JARVIS como uma mensagem normal.
"""
from __future__ import annotations

import logging

from config import settings

log = logging.getLogger("jarvis.voice_groq")

MODEL = "whisper-large-v3-turbo"
MAX_BYTES = 8 * 1024 * 1024  # ~ alguns minutos de fala em webm/opus: bem mais que um pedido
MIN_BYTES = 800  # menos que isso é só o clique do microfone
_EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
        "audio/mp4": "m4a", "audio/aac": "m4a"}


class VoiceError(Exception):
    """Erro com a mensagem para o usuário e o código HTTP."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


def available() -> bool:
    return bool(getattr(settings, "GROQ_API_KEY", ""))


def _client():
    from openai import OpenAI

    return OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1", timeout=30)


def file_name(mime: str) -> str:
    base = (mime or "").split(";")[0].strip().lower()
    return f"fala.{_EXT.get(base, 'webm')}"


def transcribe(data: bytes, mime: str = "audio/webm", client_factory=None) -> str:
    """Áudio -> texto em português. VoiceError com a mensagem certa quando não dá."""
    if not available():
        raise VoiceError("Para eu entender a sua voz aqui, conecte a Groq em Cérebro (IA). É grátis.", 409)
    if len(data) > MAX_BYTES:
        raise VoiceError("Áudio grande demais. Fale um pedido mais curto.", 413)
    if len(data) < MIN_BYTES:
        raise VoiceError("Não ouvi nada. Fale perto do microfone.", 400)
    try:
        res = (client_factory or _client)().audio.transcriptions.create(
            model=MODEL, file=(file_name(mime), data, (mime or "audio/webm").split(";")[0]),
            language="pt", response_format="json", temperature=0)
    except Exception as exc:  # noqa: BLE001 - a mensagem da Groq pode trazer detalhes: vai só para o log
        log.warning("Transcrição pela Groq falhou: %s", exc)
        raise VoiceError("A Groq não conseguiu entender o áudio agora. Tente de novo ou escreva.", 502) from exc
    return (getattr(res, "text", "") or "").strip()
