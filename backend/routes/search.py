"""Rotas da busca profunda (cota e execução)."""

from fastapi import HTTPException
from pydantic import BaseModel
from modules import tools, prefs, memory, deep_search_quota
from fastapi import APIRouter
from core import runtime, session, speech, reactive_cards, turns

router = APIRouter()


class SearchExecuteRequest(BaseModel):
    query: str
    mode: str = "browser"  # "browser" | "deep" | "api"
    remember: bool = False


@router.get("/api/search/quota")
async def get_search_quota() -> dict:
    """Retorna o status da cota diária de pesquisa profunda."""
    return deep_search_quota.get_status()


@router.post("/api/search/execute")
async def execute_search(req: SearchExecuteRequest) -> dict:
    """Executa a pesquisa no modo escolhido (navegador ou profunda com IA)."""
    query = req.query.strip()
    mode = req.mode.lower().strip()
    if mode == "api":
        mode = "deep"
    if mode not in {"deep", "browser"}:
        raise HTTPException(status_code=400, detail="Modo de busca inválido. Use 'browser' ou 'deep'.")

    session.last_search_query = query
    if req.remember and mode == "browser":
        prefs.set_search_mode(mode)

    if mode == "browser":
        reply = await tools.execute_browser_search(query)
        cards = await reactive_cards.detect_reactive_cards(f"pesquise {query}", reply)
        session.history.extend(
            [
                {"role": "user", "content": f"pesquise {query}"},
                {"role": "assistant", "content": reply},
            ]
        )
        memory.add_conversation(f"pesquise {query}", reply)
        del session.history[: -turns.MAX_HISTORY]
        await runtime.manager.broadcast({"type": "reset"})
        await runtime.manager.broadcast({"type": "response", "text": reply, "cards": cards})
        runtime.track(speech.speak(reply))
        return {"status": "ok", "mode": "browser", "response": reply, "cards": cards}
    else:
        can_run, reason = deep_search_quota.can_consume()
        if not can_run:
            raise HTTPException(status_code=429, detail=reason)
        deep_search_quota.consume()
        return await turns.handle_turn(f"pesquisa profunda sobre {query}", routine=False, force_deep=True)
