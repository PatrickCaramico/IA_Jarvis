"""V8.11: "quais são suas habilidades?" fala o resumo e abre a aba ⚡ da Central no aparelho que pediu."""
import asyncio

from core import runtime
from core.skills import registry, router


def test_lists_groups_and_opens_the_panel(real_skills, monkeypatch):
    sent = []

    async def fake_broadcast(event):
        sent.append(event)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    result = asyncio.run(router.try_fast_path("Jarvis, quais são suas habilidades?"))
    assert "janelas e monitores" in result.speech and "dossiês" in result.speech and "Abri a lista" in result.speech
    assert "abrir programa" not in result.speech
    assert sent == [{"type": "open_panel", "panel": "agents", "agent": "habilidades", "client_id": None}]
    registry.set_enabled("deep_brief", False)
    assert "dossiês" in asyncio.run(router.try_fast_path("mostra suas habilidades")).speech  # listar_dossies segue ligado


def test_phrases(real_skills):
    for phrase in ("quais sao suas habilidades", "abre a central de habilidades", "mostra as habilidades"):
        assert registry.match(phrase, phrase)[0].name == "ver_habilidades"
    assert registry.match("o que voce sabe fazer", "o que voce sabe fazer") is None
