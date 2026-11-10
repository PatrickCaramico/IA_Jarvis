"""Ações que esperam um "sim" do usuário (4.2): sugestão da rotina e organização de pasta.

`offer()` guarda a ação pendente (vale 3 minutos); o motor de conversa (core/turns.py) chama
`answer()` antes de qualquer outra coisa quando há algo pendente.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from core import session

TTL_S = 180
YES = {"sim", "pode", "pode sim", "claro", "com certeza", "confirmo", "positivo", "manda", "faz", "pode fazer",
       "ativa", "abre", "pode abrir", "pode ativar", "pode mover", "move", "organiza", "isso", "ok", "beleza",
       "pode mandar", "pode criar", "cria", "manda ver", "sim pode", "sim por favor", "pode apagar", "confirma"}
NO = {"nao", "agora nao", "hoje nao", "nao obrigado", "cancela", "cancelar", "deixa", "deixa pra la", "negativo"}
NEVER_RE = re.compile(r"\b(?:nunca|nao (?:sugira|sugere|pergunte|pergunta) mais|pare de sugerir|para de sugerir)\b")


def offer(kind: str, data: dict) -> None:
    session.pending_action = {"kind": kind, "data": data, "expires": time.time() + TTL_S}


def pending() -> Optional[dict]:
    action = session.pending_action
    if action and time.time() > action["expires"]:
        session.pending_action = None
        return None
    return action


async def answer(norm: str) -> Optional[str]:
    """`norm` normalizado (sem acentos). Devolve a resposta se a frase respondeu à pendência."""
    action = pending()
    if not action:
        return None
    kind, data = action["kind"], action["data"]
    if NEVER_RE.search(norm) and kind == "routine":
        from modules import routine

        session.pending_action = None
        routine.dismiss(data["key"], forever=True)
        return "Entendido, senhor. Não vou mais sugerir isso. Dá para reativar em Configurações, na aba Automação."
    if norm in NO:
        session.pending_action = None
        if kind == "routine":
            from modules import routine

            routine.dismiss(data["key"])
            return "Tudo bem, senhor. Hoje não pergunto de novo."
        return "Certo, senhor. Não mexi em nada."
    if norm in YES:
        session.pending_action = None
        if kind == "routine":
            from modules import routine

            return await routine.execute(data)
        if kind == "organize":
            import asyncio

            from modules import files

            return await asyncio.to_thread(files.apply_plan, data)
        # V4.5: arquivos (lixeira, mover, criar pasta) e WhatsApp, sempre depois do "sim"
        if kind in {"file_trash", "file_move", "file_mkdir"}:
            import asyncio

            from modules import files

            if kind == "file_trash":
                return await asyncio.to_thread(files.send_to_trash, data["path"])
            if kind == "file_move":
                return await asyncio.to_thread(files.move_to, data["path"], data["folder"])
            return await asyncio.to_thread(files.make_folder, data["path"])
        if kind == "whatsapp":
            from modules import whatsapp

            return whatsapp.open_chat(data)
    return None
