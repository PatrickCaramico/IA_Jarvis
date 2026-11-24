"""V9.4: modo gravar — o senhor ensina uma sequência de pedidos e depois refaz tudo pelo nome."""
import asyncio

import pytest

from core import reactive_cards, runtime, session, speech, turns
from core.skills import executor, registry, router
from modules import prefs, tools
from modules.quick_replies import _norm
from skills import modo_gravar as mg


def match(phrase):
    return registry.match(_norm(phrase), phrase)


@pytest.fixture
def env(monkeypatch, real_skills):
    sent, legacy = [], []

    async def fake_broadcast(event):
        sent.append(event)

    async def fake_speak(text, *a, **k):
        session.busy = False

    async def no_cards(message, reply):
        return []

    async def fake_tools_run(message, name=""):
        legacy.append(message)
        return "Volume em 30%, senhor." if "volume" in message else None

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(speech, "speak", fake_speak)
    monkeypatch.setattr(reactive_cards, "detect_reactive_cards", no_cards)
    monkeypatch.setattr(tools, "run", fake_tools_run)
    monkeypatch.setattr(mg, "STEP_PAUSE_S", 0)
    monkeypatch.setattr(session, "busy", False)
    return sent, legacy


def say(text):
    return asyncio.run(turns.handle_turn(text, routine=False))["response"]


def test_phrases_depend_on_state(real_skills):
    for phrase in ("modo gravar", "vou te ensinar uma rotina chamada estudo", "começa a gravar", "grava uma rotina chamada cinema"):
        hit = match(phrase)
        assert hit and hit[0].name == "gravar_inicio", phrase
    assert match("vou te ensinar uma rotina chamada estudo")[1] == {"nome": "estudo"}
    for phrase in ("começa a gravar a tela", "protocolo gravação", "para de gravar", "estudo"):
        hit = match(phrase)
        assert hit is None or not hit[0].name.startswith(("gravar_", "executar_gravacao")), phrase
    mg._load()["recording"] = {"label": "", "steps": [], "started": 0, "last": 0}
    assert match("para de gravar")[0].name == "gravar_fim"
    assert match("pronto, salva como modo cinema")[1] == {"nome": "modo cinema"}
    assert match("cancela a gravação")[0].name == "gravar_cancelar"
    assert match("modo gravar") is None or match("modo gravar")[0].name != "gravar_inicio"  # já gravando


def test_record_save_and_replay(env):
    sent, legacy = env
    prefs.update(lock_cards=["clock"])
    assert say("vou te ensinar uma rotina chamada estudo").startswith("Gravando a rotina estudo, senhor.")
    assert {"type": "recording", "active": True, "label": "estudo", "steps": 0, "max": mg.MAX_STEPS} in sent
    say("coloca o clima na tela de bloqueio")  # skill: guarda nome e parâmetros
    say("volume em trinta")  # função local: guarda a frase
    rec = mg.recording()
    assert [s["kind"] for s in rec["steps"]] == ["skill", "phrase"]
    assert rec["steps"][0]["name"] == "widgets_do_bloqueio" and rec["steps"][0]["args"] == {"widgets": ["weather"], "acao": "mostrar"}
    out = say("para de gravar")
    assert out == "Rotina estudo salva com 2 passos, senhor. Para refazer, é só dizer: estudo."
    assert mg.recording() is None and "estudo" in mg.items() and sent[-1]["type"] in {"response", "reset", "recording"}

    # refaz: a skill roda com os mesmos parâmetros e a frase vai de novo para a função local
    prefs.update(lock_cards=["clock"])
    legacy.clear()
    out = say("estudo")
    assert out == "Pronto, senhor: rotina estudo feita."
    assert prefs.get_all()["lock_cards"] == ["clock", "weather"] and legacy == ["volume em trinta"]
    assert mg.items()["estudo"]["runs"] == 1
    agent = [e for e in sent if e.get("type") == "agent" and e.get("agent") == "gravacao"]
    assert agent[0]["status"] == "working" and agent[-1]["status"] == "done"
    assert match("executa a rotina estudo")[1] == {"nome": "estudo"}


def test_empty_recording_and_cancel(env):
    say("modo gravar")
    assert say("para de gravar").startswith("Parei a gravação, senhor, mas nenhum pedido deu certo")
    say("modo gravar")
    assert say("cancela a gravação") == "Gravação cancelada, senhor. Nada foi salvo."
    assert mg.items() == {}


def test_unnamed_recording_gets_a_number_and_list(env):
    say("modo gravar")
    say("volume em trinta")
    assert say("para de gravar").startswith("Rotina rotina 1 salva com 1 passo")
    assert say("quais são as minhas gravações?") == "Sei fazer 1 rotina, senhor: rotina 1."


def test_failed_step_is_reported(env, monkeypatch):
    mg.items()["cinema"] = {"label": "cinema", "steps": [{"kind": "phrase", "message": "abre a netflix"},
                                                          {"kind": "phrase", "message": "volume em trinta"}], "runs": 0}
    out = say("executa a rotina cinema")
    assert out == "Rotina cinema feita, senhor, mas não consegui: abre a netflix."


def test_delete_asks_yes(env):
    mg.items()["cinema"] = {"label": "cinema", "steps": [{"kind": "phrase", "message": "volume em trinta"}], "runs": 0}
    out = say("apaga a rotina cinema")
    assert "Diga sim" in out and "cinema" in mg.items()
    assert say("sim") == "Rotina cinema apagada, senhor."
    assert mg.items() == {}


def test_observer_ignores_subcalls_and_own_skills():
    mg._load()["recording"] = {"label": "x", "steps": [], "started": 0, "last": 0}
    executor.notify({"kind": "skill", "name": "gravar_fim", "args": {}, "message": "para de gravar"})
    executor.notify({"kind": "other"})
    assert mg.recording()["steps"] == []
    for _ in range(mg.MAX_STEPS + 3):
        executor.notify({"kind": "phrase", "message": "volume em trinta"})
    assert len(mg.recording()["steps"]) == mg.MAX_STEPS


def test_router_still_works_without_recordings(real_skills):
    assert asyncio.run(router.try_fast_path("estudo")) is None
