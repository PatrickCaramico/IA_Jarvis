"""Skill Clipboard AI (V8.11): a IA trabalha em cima do que o senhor copiou (Ctrl+C).

Frases (caminho rápido) — a IA também pode chamar como função:
- "resume o que eu copiei", "explica o texto copiado"
- "traduz o que eu copiei" (português <-> inglês) / "traduz o que copiei para o espanhol"
- "corrige o texto que eu copiei" / "revisa o que copiei"
Traduzir e corrigir devolvem o resultado PARA a área de transferência (é só colar com Ctrl+V); resumir e explicar
falam a resposta e mostram um cartão. O texto copiado vai para a IA só quando o senhor pede. Só no Windows.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.clipboard_ai")

MAX_CHARS = 8000
LANGS = {"ingles": "inglês", "espanhol": "espanhol", "portugues": "português", "frances": "francês",
         "italiano": "italiano", "alemao": "alemão", "japones": "japonês", "chines": "chinês"}
_PT_WORDS = {"de", "que", "nao", "para", "com", "uma", "os", "as", "do", "da", "em", "voce", "isso", "mais", "por", "esta"}


# ------------------------------------------------------------------ área de transferência (Windows, ctypes)
def read_clipboard() -> str:
    from modules import desk

    return desk.read_clipboard()


def write_clipboard(text: str) -> bool:
    """Põe o texto na área de transferência do Windows. Fora do Windows: False."""
    import sys

    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    data = ctypes.create_unicode_buffer(text)
    size = ctypes.sizeof(data)
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(0x0002, size)  # GMEM_MOVEABLE
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, data, size)
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT; dá certo = o Windows fica dono da memória
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


# ------------------------------------------------------------------ partes puras
def looks_portuguese(text: str) -> bool:
    from skills.workspace.layouts import norm

    words = norm(text).split()[:200]
    if not words:
        return True
    return sum(w in _PT_WORDS for w in words) / len(words) >= 0.06


def target_language(text: str, wanted: str = "") -> str:
    from skills.workspace.layouts import norm

    key = norm(wanted).replace("o ", "", 1).strip()
    if key in LANGS:
        return LANGS[key]
    return "inglês" if looks_portuguese(text) else "português"


PROMPTS = {
    "resumir": ("Resuma o texto abaixo em português, em 2 a 4 frases curtas para serem lidas em voz alta, sem markdown, "
                "com a ideia principal primeiro."),
    "explicar": ("Explique o texto abaixo em português, de forma simples, em até 4 frases curtas para serem lidas em voz "
                 "alta, sem markdown. Se for código, diga o que ele faz."),
    "corrigir": ("Corrija ortografia, gramática e pontuação do texto abaixo, mantendo o idioma, o tom, o sentido e a "
                 "formatação (quebras de linha). Responda SÓ com o texto corrigido, sem comentários nem aspas."),
    "traduzir": ("Traduza o texto abaixo para {lang}, de forma natural, mantendo a formatação (quebras de linha). "
                 "Responda SÓ com a tradução, sem comentários nem aspas."),
}


def build_prompt(acao: str, text: str, lang: str = "") -> str:
    return PROMPTS[acao].format(lang=lang) + "\n\nTEXTO:\n" + text[:MAX_CHARS]


def clean_output(text: str) -> str:
    """Tira as aspas/cercas que a IA às vezes põe em volta."""
    out = (text or "").strip()
    out = re.sub(r"^```\w*\n?|\n?```$", "", out).strip()
    if len(out) > 1 and out[0] == out[-1] and out[0] in "\"'“”":
        out = out[1:-1].strip()
    return out


_ACTIONS = {"resume": "resumir", "resuma": "resumir", "resumir": "resumir", "traduz": "traduzir", "traduza": "traduzir",
            "traduzir": "traduzir", "corrige": "corrigir", "corrija": "corrigir", "corrigir": "corrigir",
            "revisa": "corrigir", "revise": "corrigir", "revisar": "corrigir", "explica": "explicar",
            "explique": "explicar", "explicar": "explicar"}
_CLIP_RE = re.compile(
    r"\b(?P<verb>" + "|".join(_ACTIONS) + r")\b(?:\s+(?:pra mim|para mim))?\s+(?:o\s+|a\s+|esse\s+|este\s+)?"
    r"(?:que\s+(?:eu\s+)?copiei|texto\s+(?:que\s+(?:eu\s+)?copiei|copiado)|copiado|area de transferencia|clipboard)"
    r"(?:\s+(?:pro|pra|para o|para|em)\s+(?P<lang>" + "|".join(LANGS) + r"))?\b"
)


def _parse(norm_text: str, _original: str) -> Optional[dict]:
    m = _CLIP_RE.search(norm_text)
    if not m:
        return None
    args = {"acao": _ACTIONS[m.group("verb")]}
    if m.group("lang"):
        args["idioma"] = m.group("lang")
    return args


@skill(
    name="area_de_transferencia_ia",
    title="usar o texto copiado",
    description=("Resume, explica, traduz ou corrige o texto que o usuário copiou (área de transferência). Traduzir e "
                 "corrigir deixam o resultado copiado, pronto para colar."),
    permission=Permission.ACTION,
    timeout=40,
    allow_remote=False,  # a área de transferência é a do PC
    parse=_parse,
    params={"type": "object", "required": ["acao"], "properties": {
        "acao": {"type": "string", "enum": ["resumir", "explicar", "traduzir", "corrigir"]},
        "idioma": {"type": "string", "description": "Idioma da tradução (padrão: português <-> inglês)."}}},
    examples=["resume o que eu copiei", "traduz o que eu copiei", "corrige o texto que eu copiei"],
)
def area_de_transferencia_ia(ctx: SkillContext, acao: str, idioma: str = "") -> SkillResult:
    from services import llm_orchestrator as llm

    text = (read_clipboard() or "").strip()
    if not text:
        return SkillResult(ok=False, speech="A área de transferência está vazia, ou o que foi copiado não é texto, senhor.")
    lang = target_language(text, idioma) if acao == "traduzir" else ""
    try:
        answer = clean_output(llm.ask_text(build_prompt(acao, text, lang), max_tokens=min(4000, 300 + len(text) // 2)))
    except Exception as exc:  # noqa: BLE001
        log.exception("Clipboard AI: a IA falhou")
        return SkillResult(ok=False, speech=llm.friendly_error(exc))
    if not answer:
        return SkillResult(ok=False, speech="A inteligência artificial não devolveu resposta desta vez, senhor. Tente de novo.")
    cut = " (só os primeiros 8 mil caracteres)" if len(text) > MAX_CHARS else ""
    if acao in ("resumir", "explicar"):
        tag = "RESUMO DO COPIADO" if acao == "resumir" else "EXPLICAÇÃO DO COPIADO"
        return SkillResult(speech=answer + (f" Resumi{cut}." if cut else ""),
                           cards=[{"type": "skill", "data": {"tag": tag, "source": f"{len(text)} caracteres",
                                                             "rows": [{"label": "", "value": answer[:900]}]}}])
    copied = write_clipboard(answer)
    what = f"traduzido para o {lang}" if acao == "traduzir" else "corrigido"
    tail = " Já está na área de transferência; é só colar." if copied else " Não consegui copiar; o texto ficou na tela."
    preview = answer if len(answer) <= 900 else answer[:900] + "…"
    return SkillResult(speech=f"Pronto, senhor: texto {what}{cut}.{tail}",
                       cards=[{"type": "skill", "data": {"tag": "TRADUÇÃO" if acao == "traduzir" else "TEXTO CORRIGIDO",
                                                         "source": "copiado ✓" if copied else "não copiado",
                                                         "rows": [{"label": "", "value": preview}]}}],
                       data={"resultado": answer[:2000]})
