"""V8.7.2: prioridade dos processos do JARVIS no Windows.

Na hora de atualizar, o JARVIS faz várias coisas pesadas de uma vez (baixar, conferir arquivos, religar, carregar os
modelos e às vezes montar a interface). Com a mesma prioridade do navegador, isso fazia um vídeo do YouTube
engasgar. Com prioridade BAIXA, o Windows dá a vez para o que você está usando e o JARVIS usa o que sobrar.
Fora do Windows, nada muda.
"""
from __future__ import annotations

import logging
import sys

log = logging.getLogger("jarvis.priority")

CLASSES = {"idle": 0x00000040, "below": 0x00004000, "normal": 0x00000020}


def creationflags(level: str = "below") -> int:
    """Flag para subprocess (o processo filho, e os filhos dele, nascem com essa prioridade). 0 fora do Windows."""
    return CLASSES.get(level, 0) if sys.platform == "win32" else 0


def set_self(level: str) -> bool:
    """Muda a prioridade DESTE processo. Falso fora do Windows ou se não deu."""
    if sys.platform != "win32" or level not in CLASSES:
        return False
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        return bool(k32.SetPriorityClass(k32.GetCurrentProcess(), CLASSES[level]))
    except Exception as exc:  # noqa: BLE001
        log.info("Não consegui mudar a prioridade: %s", exc)
        return False
