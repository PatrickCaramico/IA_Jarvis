"""V7.9: conversa direta com os agentes (abas da Central, "@nome" no campo de conversa e voz).

POST   /api/agents/chat          {agent, message}  -> resposta, ações feitas, ações pendentes (CONFIRMAR)
POST   /api/agents/chat/confirm  {agent, acao}     -> roda uma ação pendente que o usuário confirmou
GET    /api/agents/chat/{agent}                    -> conversa salva (últimas 30 mensagens)
DELETE /api/agents/chat/{agent}                    -> LIMPAR a conversa daquele agente
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import runtime

log = logging.getLogger("jarvis.agent_chat")
router = APIRouter()


def _agent(name: str) -> str:
    from modules import agent_chat

    key = agent_chat.resolve(name)
    if not key:
        raise HTTPException(status_code=404, detail=f"Não conheço o agente \"{name}\".")
    return key


class ChatRequest(BaseModel):
    agent: str
    message: str
    speak: bool = True


@router.post("/api/agents/chat")
async def agent_chat_send(req: ChatRequest) -> dict:
    from core import speech
    from modules import agent_chat, agents
    from services import llm_orchestrator

    key = _agent(req.agent)
    message = (req.message or "").strip()[:1000]
    if not message:
        raise HTTPException(status_code=400, detail="Escreva a mensagem para o agente.")
    prompt = await asyncio.to_thread(agent_chat.build_prompt, key, message)
    agent_chat.record(key, "user", message)
    try:
        raw = await asyncio.to_thread(llm_orchestrator.ask_text, prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("Agente %s: a IA falhou: %s", key, exc)
        raise HTTPException(status_code=502, detail="O agente não conseguiu responder agora.") from exc
    reply, actions = agent_chat.parse(key, raw or "")
    done, pending, holo, sources = [], [], "", []
    for a in actions:
        try:
            if a["tipo"] == "rota":
                await agents.handle(f"quero ir para {a['destino']}" + (f" de {a['modo']}" if a.get("modo") else ""))
                done.append("✓ " + agent_chat.describe(a))
            elif a["tipo"] == "youtube":
                await agents.handle(f"procura {a['busca']} no youtube")
                done.append("✓ " + agent_chat.describe(a))
            elif a["tipo"] == "web":
                answer = await asyncio.to_thread(
                    llm_orchestrator.ask_text, f"Pesquise na internet e responda em 2 a 5 frases curtas, em português: {a['consulta']}", True)
                if answer:
                    reply = answer
                    sources = [{"name": s.get("name", ""), "url": s.get("url", "")}
                               for s in (llm_orchestrator.get_last_grounding_data().get("sources") or [])[:4] if s.get("url")]
            elif a["tipo"] == "holograma":
                holo = a["tema"]
                done.append("✓ " + agent_chat.describe(a))
            elif agent_chat.needs_confirm(a):
                pending.append({**a, "descricao": agent_chat.describe(a)})
            else:
                done.append(await asyncio.to_thread(agent_chat.run_action, a))
        except Exception as exc:  # noqa: BLE001 - uma ação ruim não derruba a resposta
            log.warning("Agente %s: ação %s falhou: %s", key, a.get("tipo"), exc)
            done.append(f"Não consegui: {agent_chat.describe(a)}")
    agent_chat.record(key, "agent", reply, {"done": done, "pending": pending, "sources": sources})
    if req.speak:
        runtime.track(speech.speak(reply))
    a = agent_chat.AGENTS[key]
    return {"agent": key, "label": a["label"], "icon": a["icon"], "reply": reply, "done": done,
            "pending": pending, "holo": holo, "sources": sources}


class ConfirmRequest(BaseModel):
    agent: str
    acao: dict


@router.post("/api/agents/chat/confirm")
async def agent_chat_confirm(req: ConfirmRequest) -> dict:
    from modules import agent_chat, shopping

    key = _agent(req.agent)
    action = agent_chat.clean_action(key, req.acao)
    if not action or action["tipo"] in ("rota", "youtube", "web", "holograma"):
        raise HTTPException(status_code=400, detail="Ação inválida para este agente.")
    text = await asyncio.to_thread(agent_chat.run_action, action)
    agent_chat.record(key, "agent", text)
    if action["tipo"].startswith("compras"):
        await shopping.announce()
    return {"status": "ok", "text": text}


@router.get("/api/agents/chat/{agent}")
async def agent_chat_history(agent: str) -> dict:
    from modules import agent_chat

    key = _agent(agent)
    return {"agent": key, "messages": agent_chat.history(key)}


@router.delete("/api/agents/chat/{agent}")
async def agent_chat_clear(agent: str) -> dict:
    from modules import agent_chat

    key = _agent(agent)
    agent_chat.clear(key)
    return {"agent": key, "messages": []}
