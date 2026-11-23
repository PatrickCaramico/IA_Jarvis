"""Música de entrada (V8.13): "toca a música do Homem de Ferro" / "toca Back in Black".

Toca a música de entrada escolhida (padrão: Back in Black, do AC/DC, a do Homem de Ferro) no Spotify do usuário.
Nada de música embutida no JARVIS: ela é buscada e tocada pela conta dele (precisa do Spotify conectado).
A mesma música toca sozinha ao entrar na central (preferência "intro_song_on_entry", rota /api/lock/intro-music)
e quando o botão VOZ do topo da central abre.
"""
from __future__ import annotations

import logging

from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.musica_de_entrada")

DEFAULT_SONG = "Back in Black AC/DC"


def song_query() -> str:
    from modules import prefs

    return (prefs.get_all().get("intro_song") or DEFAULT_SONG).strip() or DEFAULT_SONG


@skill(
    name="musica_de_entrada",
    title="tocar a música de entrada",
    description=("Toca a música de entrada do usuário no Spotify (padrão: Back in Black, do AC/DC, a música do "
                 "Homem de Ferro). Use quando ele pedir a música do Homem de Ferro, Back in Black ou a música de entrada."),
    permission=Permission.ACTION,
    timeout=20,
    triggers=[
        r"\b(?:toca|toque|tocar|coloca|coloque|bota|solta|manda|play)\b.*\b(?:back in black|musica do homem de ferro|"
        r"tema do homem de ferro|musica de entrada|musica do iron man)\b",
        r"^(?:jarvis\s+)?(?:ativa\s+(?:o\s+)?)?modo\s+homem\s+de\s+ferro$",
    ],
    params={"type": "object", "properties": {}},
    examples=["toca a música do Homem de Ferro", "toca Back in Black"],
)
def musica_de_entrada(ctx: SkillContext) -> SkillResult:
    from modules import spotify

    if not spotify.connected():
        return SkillResult(ok=False, speech="Para tocar a música de entrada, conecte o Spotify em Configurações, senhor.")
    query = song_query()
    try:
        reply = spotify.search_and_play(query, False)
    except spotify.SpotifyError as exc:  # V8.13.2: sem aparelho (mesmo depois de abrir o app) ou sem Premium
        log.warning("Spotify recusou a música de entrada: %s", exc.code)
        if exc.code == "premium":
            return SkillResult(ok=False, speech="O Spotify só deixa eu escolher a música com uma conta Premium, senhor.")
        return SkillResult(ok=False, speech="Não achei o Spotify aberto em nenhum aparelho, senhor. Abra o Spotify e tente de novo.")
    except RuntimeError:  # autorização expirou
        log.exception("Spotify recusou a música de entrada")
        return SkillResult(ok=False, speech="A autorização do Spotify expirou, senhor. Conecte de novo em Configurações.")
    except Exception:  # noqa: BLE001
        log.exception("Falha ao tocar a música de entrada")
        return SkillResult(ok=False, speech="Não consegui tocar a música de entrada agora, senhor.")
    if reply.startswith("Não encontrei"):
        return SkillResult(ok=False, speech=f"Não encontrei {query} no Spotify, senhor.")
    return SkillResult(speech="Back in Black, senhor. Sistemas no máximo." if query == DEFAULT_SONG else reply,
                       data={"musica": query})
