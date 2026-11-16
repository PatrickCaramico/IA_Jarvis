"""V8.5.0: ATUALIZAÇÃO AUTOMÁTICA (sem abrir a pasta nem o CMD).

De tempos em tempos o JARVIS confere se tem versão nova no GitHub. Se tiver, espera um momento em que ele está
PARADO (ninguém falando com ele há alguns minutos, nada rodando) e atualiza sozinho, igual ao botão ATUALIZAR,
mas sem falar: só avisa na ilha. Depois do reinício:
- a interface nova vem pronta do site (ou é montada em segundo plano);
- a ilha e a janela do app se recarregam sozinhas;
- o app do Windows se reabre sozinho quando o código dele mudou (desktop/jarvis_desktop.py).
Dá para desligar em Configurações › Atualizações (Modo Desk).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

log = logging.getLogger("jarvis.auto_update")

FIRST_CHECK_S = 10 * 60  # deixa o JARVIS ligar com calma
CHECK_EVERY_S = 30 * 60
QUIET_FOR_S = 5 * 60  # ninguém falou com ele por esse tempo


def enabled() -> bool:
    try:
        from modules import desk

        return bool(desk.config().get("atualizacao", {}).get("automatica", True))
    except Exception:  # noqa: BLE001
        return False


def is_quiet(now: float | None = None) -> bool:
    """O JARVIS está parado? (nada rodando, ilha parada e nenhuma resposta nos últimos minutos)."""
    from core import runtime, session

    now = time.time() if now is None else now
    if session.busy or runtime.island_state(now) != "idle":
        return False
    return now - float(runtime.ISLAND.get("resposta_em") or 0) > QUIET_FOR_S


async def check_and_update(sleep=asyncio.sleep, now=time.time) -> str:
    """Uma rodada: "desligada" | "em dia" | "ocupado" | "atualizando" | "erro"."""
    from core import runtime
    from modules import self_update

    if not enabled():
        return "desligada"
    info = await asyncio.to_thread(self_update.check, True)
    if not info.get("available"):
        return "em dia"
    for _ in range(12):  # espera até ~1 h por um momento parado
        if is_quiet(now()):
            break
        await sleep(5 * 60)
    else:
        return "ocupado"
    latest = info.get("latest") or "nova"
    log.info("Atualização automática: versão %s encontrada, atualizando com o JARVIS parado.", latest)
    runtime.note_island({"type": "response", "text": f"⬆ Atualizando o JARVIS para a versão {latest}… volto em instantes."})
    from routes.system import perform_update

    res = await perform_update(announce=False)
    return "atualizando" if res.get("status") == "restarting" else "erro"


async def auto_update_loop() -> None:
    if os.name != "nt":  # o reinício automático é pelo Iniciar-JARVIS.bat (Windows)
        return
    await asyncio.sleep(FIRST_CHECK_S)
    while True:
        try:
            if await check_and_update() == "atualizando":
                return
        except Exception as exc:  # noqa: BLE001 - sem internet etc.: tenta na próxima
            log.info("Atualização automática: não deu agora (%s).", exc)
        await asyncio.sleep(CHECK_EVERY_S)
