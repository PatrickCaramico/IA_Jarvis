"""V6.5.8: escolher a saída de áudio (onde a voz do JARVIS toca no PC) e o microfone do ouvido offline.

Os nomes vêm do SDL (o mesmo motor de som que toca a voz), como o Windows mostra:
"Alto-falantes (USB PnP Audio Device)", "Microfone (USB PnP Audio Device)". Vazio = o padrão do Windows.
Nada pessoal: o botão fica na tela de bloqueio, como o de trocar o fundo.
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

log = logging.getLogger("jarvis.audio_devices")


def _sdl_names(capture: bool) -> list[str]:
    try:
        import pygame
        from pygame._sdl2 import audio as sdl_audio

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        names = sdl_audio.get_audio_device_names(capture) or []
        return [n.decode("utf-8", "replace") if isinstance(n, bytes) else str(n) for n in names]
    except Exception as exc:  # noqa: BLE001 - sem placa de som / SDL antigo: lista vazia (fica o padrão)
        log.warning("Não consegui listar os aparelhos de som: %s", exc)
        return []


def outputs() -> list[str]:
    return _sdl_names(False)


def inputs() -> list[str]:
    return _sdl_names(True)


def snapshot() -> dict:
    from modules import prefs

    p = prefs.get_all()
    return {
        "outputs": outputs(),
        "output": p.get("audio_output_device") or "",
        "inputs": inputs(),
        "input": p.get("voice_input_device") or "",
    }


def choose(output: str | None = None, input_: str | None = None) -> dict:
    """Grava a escolha ("" = padrão do Windows). Nome que não existe é recusado (ValueError)."""
    from modules import prefs

    patch = {}
    if output is not None:
        if output and output not in outputs():
            raise ValueError("Saída de áudio não encontrada.")
        patch["audio_output_device"] = output
    if input_ is not None:
        if input_ and input_ not in inputs():
            raise ValueError("Microfone não encontrado.")
        patch["voice_input_device"] = input_
    if patch:
        prefs.update(**patch)
    return snapshot()
