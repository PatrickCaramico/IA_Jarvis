"""Memória 'Sobre mim': texto que o usuário escreve sobre si e que o JARVIS usa nas respostas."""
from config import settings

PATH = settings.DATA_DIR / "sobre_mim.txt"
MAX_CHARS = 4000


def get_about() -> str:
    try:
        return PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_about(text: str) -> str:
    text = (text or "").strip()[:MAX_CHARS]
    PATH.write_text(text, encoding="utf-8")
    return text
