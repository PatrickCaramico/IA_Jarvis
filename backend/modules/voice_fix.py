"""V6.5.14: entender melhor o que foi falado antes de procurar o comando.

O reconhecimento de voz às vezes erra o nome ("iutubi", "espotifai", "netiflix") ou corta o verbo
(só "YouTube" em vez de "abre o YouTube"). Aqui:
  1. corrige as trocas mais comuns de nomes de sites/apps e de verbos ("abri o" -> "abre o");
  2. nome de site/app sozinho ("YouTube", "o Netflix", "Spotify aí") vira "abrir <nome>", como na Alexa;
  3. nome parecido com um conhecido ("youtub", "netflx") é aproximado (difflib).
Tudo trabalha no texto normalizado (minúsculo e sem acento) e nunca mexe em frases longas.
"""
from __future__ import annotations

import difflib
import re

# troca falada -> nome certo (aplicado por palavra/expressão inteira)
_FIXES = {
    "you tube": "youtube", "iutubi": "youtube", "iutube": "youtube", "yutube": "youtube", "youtub": "youtube",
    "iou tube": "youtube", "you tubi": "youtube", "yotube": "youtube",
    "net flix": "netflix", "netflics": "netflix", "netiflix": "netflix", "netflixe": "netflix",
    "espotifai": "spotify", "spotifai": "spotify", "spotfy": "spotify", "spot fy": "spotify", "espotify": "spotify",
    "whats app": "whatsapp", "uatsap": "whatsapp", "uatizap": "whatsapp", "zap zap": "whatsapp",
    "gugou": "google", "gogle": "google", "goglo": "google",
    "insta gram": "instagram", "instagran": "instagram",
    "chat gpt": "chatgpt", "chat gepete": "chatgpt", "chat gpe te": "chatgpt",
    "g mail": "gmail", "gimail": "gmail", "ji mail": "gmail",
    "twitch tv": "twitch", "tuitch": "twitch",
    "prime vidio": "prime video", "disney mais": "disney plus", "disney+": "disney plus",
}
# verbo mal ouvido no começo -> verbo de abrir
_VERB_FIXES = (
    (r"^(?:abri|abro|habra|abrao)\b", "abre"),
)
# "vai no YouTube", "entra no Netflix", "coloca o YouTube": só vira "abrir" se o resto for um nome conhecido
_GO_TO = re.compile(r"^(?:entra|entre|vai|va|coloca|coloque|bota|bote|poe|ponha)\s+(?:no|na|o|a)\s+(.+)$")
_FILLER_TAIL = re.compile(r"\s+(?:ai|ae|pra mim|por favor|agora|rapidinho)$")
_ARTICLE = re.compile(r"^(?:o|a|os|as)\s+")


def apply_fixes(norm: str) -> str:
    text = f" {norm} "
    for wrong, right in _FIXES.items():
        text = text.replace(f" {wrong} ", f" {right} ")
    text = text.strip()
    for pattern, repl in _VERB_FIXES:
        text = re.sub(pattern, repl, text)
    return re.sub(r"\s+", " ", text).strip()


def closest(name: str, known: list[str], cutoff: float = 0.8) -> str | None:
    """Nome conhecido mais parecido (para "netflx", "youtub"...)."""
    if not name or len(name) < 4:
        return None
    hit = difflib.get_close_matches(name, known, n=1, cutoff=cutoff)
    return hit[0] if hit else None


def bare_target(norm: str, known: list[str]) -> str | None:
    """"youtube", "o netflix", "spotify ai" -> o nome conhecido; frase com mais coisa -> None."""
    text = _FILLER_TAIL.sub("", norm.strip())
    text = re.sub(r"^(?:jarvis\s+)", "", text)
    go = _GO_TO.match(text)
    if go:
        text = go.group(1)
    text = _ARTICLE.sub("", text).strip()
    if not text or len(text.split()) > 3:
        return None
    if text in known:
        return text
    return closest(text, known, cutoff=0.86)
