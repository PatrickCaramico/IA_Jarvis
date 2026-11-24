"""Tela de bloqueio por voz (V9.4): widgets fixos com animação e o avatar holográfico.

Antes: os cartões do bloqueio (relógio, clima, Spotify, água, próximo jogo) só mudavam em Configurações > Bloqueio,
e o clima era um número parado. Agora:
  - "deixa o clima sempre aparecer na tela de bloqueio" fixa o widget (vale para relógio, clima, Spotify, água e
    próximo jogo, um ou vários na mesma frase). O clima ganha a animação do tempo de agora (sol girando, nuvens,
    chuva, raio, noite estrelada) e todo widget novo entra com uma animação;
  - "tira a água da tela de bloqueio" esconde;
  - "coloca meu avatar na tela de bloqueio" liga o avatar holográfico feito da foto do rosto (modules/holo_avatar.py).
A tela bloqueada muda na hora (prefs_updated). Nada pessoal entra no bloqueio: só o que já era público.
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

# palavra falada -> chave do cartão (modules/prefs.py LOCK_CARD_KEYS) ou "avatar"
_WIDGETS = [
    ("weather", r"clima|tempo|previsao(?: do tempo)?|temperatura"),
    ("clock", r"relogio|hora|horario"),
    ("spotify", r"spotify|musica|o que (?:esta|ta) tocando"),
    ("water", r"agua|hidratacao"),
    ("fan_match", r"(?:proximo )?jogo|futebol|palmeiras|placar"),
    ("avatar", r"avatar|(?:meu )?rosto|holograma"),
]
NAMES = {"weather": "o clima", "clock": "o relógio", "spotify": "o Spotify", "water": "a água de hoje",
         "fan_match": "o próximo jogo", "avatar": "o seu avatar"}

_PLACE = re.compile(r"\b(?:na|no|da|do|pra|para a|para o)\s+(?:tela\s+(?:de\s+)?bloqueio|tela\s+bloqueada|bloqueio)\b")
_ADD = re.compile(r"\b(?:deixa|deixe|coloca|coloque|poe|ponha|bota|mostra|mostre|fixa|fixe|adiciona|adicione|quero|"
                  r"liga|ligue|ativa|ative|aparece|aparecer)\b")
_REMOVE = re.compile(r"\b(?:tira|tire|remove|remova|esconde|esconda|desliga|desligue|desativa|desative|some com|"
                     r"nao (?:quero|mostra|mostre))\b")


def widgets_in(norm: str) -> list[str]:
    found = []
    for key, rx in _WIDGETS:
        if re.search(rf"\b(?:{rx})\b", norm):
            found.append(key)
    return found


def _parse(norm: str, _original: str) -> Optional[dict]:
    if not _PLACE.search(norm):
        return None
    keys = widgets_in(norm)
    if not keys:
        return None
    if _REMOVE.search(norm):
        acao = "tirar"
    elif _ADD.search(norm):
        acao = "mostrar"
    else:
        return None
    return {"widgets": keys, "acao": acao}


def apply(current: list[str], avatar: bool, widgets: list[str], show: bool) -> tuple[list[str], bool, list[str], list[str]]:
    """Parte pura: (cartões novos, avatar, o que mudou, o que já estava assim)."""
    cards, changed, same = list(current), [], []
    for key in widgets:
        if key == "avatar":
            (same if avatar == show else changed).append(key)
            avatar = show
            continue
        if show and key not in cards:
            cards.append(key)
            changed.append(key)
        elif not show and key in cards:
            cards.remove(key)
            changed.append(key)
        else:
            same.append(key)
    return cards, avatar, changed, same


def _names(keys: list[str]) -> str:
    from skills.workspace.layouts import spoken_list

    return spoken_list([NAMES[k] for k in keys])


@skill(
    name="widgets_do_bloqueio",
    title="mudar a tela de bloqueio",
    description=("Mostra ou tira widgets da tela de bloqueio (relógio, clima com animação, Spotify, água de hoje, "
                 "próximo jogo) e liga ou desliga o avatar holográfico feito da foto do rosto do usuário."),
    permission=Permission.ACTION,
    timeout=10,
    parse=_parse,
    params={"type": "object", "required": ["widgets", "acao"], "properties": {
        "widgets": {"type": "array", "items": {"type": "string", "enum": [k for k, _ in _WIDGETS]}},
        "acao": {"type": "string", "enum": ["mostrar", "tirar"]},
    }},
    examples=["deixa o clima sempre aparecer na tela de bloqueio", "tira a água da tela de bloqueio",
              "coloca meu avatar na tela de bloqueio"],
)
async def widgets_do_bloqueio(ctx: SkillContext, widgets: list, acao: str) -> SkillResult:
    from modules import face, prefs

    show = acao == "mostrar"
    p = await asyncio.to_thread(prefs.get_all)
    want = list(dict.fromkeys(widgets))
    if show and "avatar" in want and not face.has_profile():
        return SkillResult(ok=False, speech="Para o avatar, preciso da foto do seu rosto cadastrada, senhor. "
                                            "Ela fica em Configurações, Bloqueio.")
    cards, avatar, changed, same = apply(list(p.get("lock_cards") or []), bool(p.get("lock_avatar_enabled")), want, show)
    if changed:
        await asyncio.to_thread(prefs.update, lock_cards=cards, lock_avatar_enabled=avatar)
        await ctx.broadcast({"type": "prefs_updated", "lock_cards": cards, "lock_avatar_enabled": avatar,
                             "lock_cards_new": [k for k in changed if show]})
    if not changed:
        where = "já está" if len(same) == 1 else "já estão"
        if not show:
            where = "já não aparece" if len(same) == 1 else "já não aparecem"
        return SkillResult(speech=f"{_names(same).capitalize()} {where} na tela de bloqueio, senhor.")
    if show:
        extra = " O clima entra com a animação do tempo de agora." if "weather" in changed else ""
        if "fan_match" in changed and not p.get("fan_mode_enabled"):
            extra += " O próximo jogo aparece quando o Modo Torcedor estiver ligado."
        speech = f"Pronto, senhor: {_names(changed)} fica sempre na tela de bloqueio.{extra}"
        if len(changed) > 1:
            speech = speech.replace(" fica ", " ficam ")
    else:
        speech = f"Pronto, senhor: tirei {_names(changed)} da tela de bloqueio."
    return SkillResult(speech=speech)
