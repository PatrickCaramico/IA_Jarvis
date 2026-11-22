"""V8.11: motor das Skills (plug-and-play): declaração, auto-discovery, executor, caminho rápido e IA."""
import asyncio
import sys
import textwrap
import time
from types import SimpleNamespace

import pytest

from core import confirm, session
from core.skills import Permission, SkillContext, SkillResult, executor, registry, router
from core.skills.base import SkillDefinitionError, build_skill
from modules import access


@pytest.fixture(autouse=True)
def _clean_registry():
    registry.reset_for_tests()
    access.reset_for_tests(access.UNLOCKED)
    session.pending_action = None
    yield
    registry.reset_for_tests()
    session.pending_action = None
    access.reset_for_tests(access.LOCKED)


def _add(fn, **options):
    options.setdefault("name", fn.__name__)
    options.setdefault("description", "Skill de teste.")
    sk = build_skill(fn, **options)
    registry.register(sk)
    return sk


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ declaração
def test_definition_is_validated():
    async def ok(ctx):
        return SkillResult(speech="oi")

    async def no_ctx(texto):
        return SkillResult()

    with pytest.raises(SkillDefinitionError):
        build_skill(ok, name="Nome Ruim", description="x")
    with pytest.raises(SkillDefinitionError):
        build_skill(ok, name="sem_descricao", description=" ")
    with pytest.raises(SkillDefinitionError):
        build_skill(ok, name="apagar_tudo", description="x", permission=Permission.CRITICAL, public=True)
    with pytest.raises(SkillDefinitionError):
        build_skill(no_ctx, name="sem_ctx", description="x")
    with pytest.raises(SkillDefinitionError):
        build_skill(ok, name="schema_ruim", description="x", params={"type": "object", "properties": {"a": {}}})
    with pytest.raises(SkillDefinitionError):
        build_skill(ok, name="regex_ruim", description="x", triggers=["(abc"])
    assert build_skill(ok, name="critica", description="x", permission="critical").allow_remote is False


# ------------------------------------------------------------------ auto-discovery
def test_discovery_loads_good_skills_and_reports_broken_ones(tmp_path, monkeypatch):
    pkg = tmp_path / "skills_teste_811"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "boa.py").write_text(textwrap.dedent('''
        from core.skills import skill, SkillResult

        @skill(name="boa_skill", description="Uma skill boa.", triggers=[r"^diga oi$"])
        async def boa(ctx):
            return SkillResult(speech="oi")
    '''), encoding="utf-8")
    (pkg / "quebrada.py").write_text("import modulo_que_nao_existe\n", encoding="utf-8")
    (pkg / "declaracao_ruim.py").write_text(textwrap.dedent('''
        from core.skills import skill

        @skill(name="X", description="nome inválido")
        async def ruim(ctx):
            return None
    '''), encoding="utf-8")
    (pkg / "_rascunho.py").write_text("raise RuntimeError('não deveria carregar')\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        registry.load(package="skills_teste_811", force=True)
        assert [s.name for s in registry.all_skills()] == ["boa_skill"]
        errs = " | ".join(registry.errors())
        assert "quebrada" in errs and "Nome inválido" in errs and "rascunho" not in errs
    finally:
        for mod in [m for m in sys.modules if m.startswith("skills_teste_811")]:
            del sys.modules[mod]


def test_template_skill_is_valid_and_not_autoloaded():
    import importlib

    registry.load(force=True)  # a pasta real de skills
    assert registry.get("exemplo_eco") is None  # _template.py começa com "_"
    importlib.import_module("skills._template")
    registry._collect()
    sk = registry.get("exemplo_eco")
    assert sk is not None and sk.permission is Permission.READ
    assert registry.match("repita bom dia", "repita bom dia")[1] == {"texto": "bom dia"}


# ------------------------------------------------------------------ caminho rápido
def test_fast_path_uses_named_groups_and_skips_missing_params():
    async def volume(ctx, nivel: int):
        return SkillResult(speech=f"volume {nivel}")

    _add(volume, triggers=[r"\bvolume (?P<nivel>\d+)\b", r"\bvolume\b"],
         params={"type": "object", "properties": {"nivel": {"type": "integer"}}, "required": ["nivel"]})
    result = run(router.try_fast_path("Jarvis, volume 30"))
    assert result.speech == "volume 30"  # "30" virou inteiro
    assert run(router.try_fast_path("aumenta o volume")) is None  # sem o número: fica para a IA


def test_disabled_skill_is_ignored(monkeypatch):
    async def oi(ctx):
        return SkillResult(speech="oi")

    _add(oi, triggers=[r"^oi skill$"])
    registry.set_enabled("oi", False)
    assert run(router.try_fast_path("oi skill")) is None
    assert run(executor.execute("oi", {})).ok is False
    registry.set_enabled("oi", True)
    assert run(router.try_fast_path("oi skill")).speech == "oi"


# ------------------------------------------------------------------ executor
def test_timeout_and_circuit_breaker(monkeypatch):
    async def lenta(ctx):
        await asyncio.sleep(5)

    _add(lenta, timeout=0.05)
    for _ in range(registry.BREAKER_FAILURES):
        result = run(executor.execute("lenta", {}))
        assert result.ok is False and "demorou" in result.speech
    assert registry.paused_for("lenta") > 0
    assert "pausa" in run(executor.execute("lenta", {})).speech
    assert registry.stats("lenta").failures == registry.BREAKER_FAILURES


def test_errors_are_contained_and_sync_handlers_run_in_a_thread():
    import threading

    main_thread = threading.get_ident()

    def bloqueante(ctx):
        return "outra thread" if threading.get_ident() != main_thread else "laço principal"

    async def quebra(ctx):
        raise RuntimeError("boom")

    _add(bloqueante)
    _add(quebra)
    assert run(executor.execute("bloqueante", {})).speech == "outra thread"
    result = run(executor.execute("quebra", {}))
    assert result.ok is False and "boom" not in result.speech
    assert "boom" in registry.stats("quebra").last_error


def test_arguments_are_checked_against_the_schema():
    async def tema(ctx, cor: str, forte: bool = False):
        return SkillResult(speech=f"{cor} {forte}")

    _add(tema, params={"type": "object", "required": ["cor"], "properties": {
        "cor": {"type": "string", "enum": ["azul", "verde"]}, "forte": {"type": "boolean"}}})
    assert run(executor.execute("tema", {"cor": "azul", "forte": "sim", "extra": 1})).speech == "azul True"
    assert run(executor.execute("tema", {"cor": "roxo"})).ok is False
    assert run(executor.execute("tema", {})).ok is False


def test_restricted_mode_only_runs_public_skills(isolated_data, credentials):
    async def segredo(ctx):
        return SkillResult(speech="agenda pessoal")

    async def hora(ctx):
        return SkillResult(speech="são dez horas")

    _add(segredo, triggers=[r"^segredo$"])
    _add(hora, triggers=[r"^hora publica$"], public=True)
    access.reset_for_tests(access.LOCKED)
    assert run(executor.execute("segredo", {})).ok is False
    assert run(router.try_fast_path("segredo", public_only=True)) is None

    from modules import sentinel

    answer = run(sentinel.classify_and_answer("hora publica", "locked"))
    assert answer["public"] is True and answer["reply"] == "são dez horas"


def test_critical_skill_asks_first_and_runs_after_yes():
    done = []

    async def apagar(ctx, alvo: str):
        done.append(alvo)
        return SkillResult(speech=f"{alvo} apagado.")

    _add(apagar, permission=Permission.CRITICAL, confirm_text=lambda a: f"Apago {a['alvo']}?",
         params={"type": "object", "properties": {"alvo": {"type": "string"}}, "required": ["alvo"]})
    result = run(executor.execute("apagar", {"alvo": "rascunho"}, SkillContext(origin="llm")))
    assert result.pending and result.speech == "Apago rascunho?" and done == []
    assert run(confirm.answer("sim")) == "rascunho apagado."
    assert done == ["rascunho"]


def test_critical_skill_refuses_remote_requests():
    async def desligar(ctx):
        return SkillResult(speech="desligando")

    _add(desligar, permission=Permission.CRITICAL)
    result = run(executor.execute("desligar", {}, SkillContext(remote=True)))
    assert result.ok is False and session.pending_action is None


def test_skills_compose_with_ctx_call():
    async def base_skill(ctx, n: int):
        return SkillResult(speech=str(n * 2))

    async def composta(ctx):
        sub = await ctx.call("base_skill", n=21)
        return SkillResult(speech=f"resultado {sub.speech}")

    _add(base_skill, params={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]})
    _add(composta)
    assert run(executor.execute("composta", {})).speech == "resultado 42"


# ------------------------------------------------------------------ IA (function calling)
def _llm_setup(monkeypatch, provider):
    from services import llm_orchestrator as llm

    monkeypatch.setattr(llm.prefs, "get_llm_config", lambda: (provider, "direto"))
    monkeypatch.setattr(llm.memory, "prompt_context", lambda: "")
    monkeypatch.setattr(llm, "get_name", lambda: "")
    monkeypatch.setattr(llm, "get_about", lambda: "")
    return llm


def _weather_skill(calls):
    async def clima_teste(ctx, cidade: str):
        calls.append((cidade, ctx.origin))
        return SkillResult(speech=f"Em {cidade}, 25 graus.", cards=[{"type": "teste", "cidade": cidade}])

    _add(clima_teste, description="Clima de uma cidade.",
         params={"type": "object", "properties": {"cidade": {"type": "string"}}, "required": ["cidade"]})


def test_groq_function_call_runs_the_skill(monkeypatch):
    llm = _llm_setup(monkeypatch, "groq")
    calls, seen = [], {}
    _weather_skill(calls)

    def create(**kw):
        seen.update(kw)
        call = SimpleNamespace(id="c1", function=SimpleNamespace(name="clima_teste", arguments='{"cidade": "Recife"}'))
        msg = SimpleNamespace(content=None, tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm.settings, "GROQ_API_KEY", "chave-teste")
    monkeypatch.setattr(llm, "_client", lambda *a, **k: fake)

    async def scenario():
        text = await llm.generate_jarvis_response("como está o tempo em Recife?")
        return text, llm.take_skill_cards()

    text, cards = run(scenario())
    assert text == "Em Recife, 25 graus."
    assert calls == [("Recife", "llm")]
    assert cards == [{"type": "teste", "cidade": "Recife"}]
    assert seen["tools"][0]["function"]["name"] == "clima_teste"


def test_gemini_function_call_runs_the_skill(monkeypatch):
    llm = _llm_setup(monkeypatch, "gemini")
    calls, configs = [], []
    _weather_skill(calls)

    def generate_content(model, contents, config):
        configs.append(config)
        return SimpleNamespace(function_calls=[SimpleNamespace(name="clima_teste", args={"cidade": "Natal"})],
                               candidates=[])

    fake = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "chave-teste")
    monkeypatch.setattr(llm, "_client", lambda *a, **k: fake)
    assert run(llm.generate_jarvis_response("e o tempo em Natal?")) == "Em Natal, 25 graus."
    assert calls == [("Natal", "llm")]
    assert configs[0].automatic_function_calling.disable is True
    assert configs[0].tools[0].function_declarations[0].name == "clima_teste"


def test_no_skills_offered_with_web_search(monkeypatch):
    llm = _llm_setup(monkeypatch, "groq")
    _weather_skill([])
    assert llm._tool_session("pergunta", routine=False, deep=True, frame=False) is None
    assert llm._tool_session("pergunta", routine=True, deep=False, frame=False) is None


def test_llm_critical_call_only_asks(monkeypatch):
    llm = _llm_setup(monkeypatch, "groq")
    done = []

    async def fechar_programa(ctx, nome: str):
        done.append(nome)
        return SkillResult(speech="fechado")

    _add(fechar_programa, permission=Permission.CRITICAL, confirm_text=lambda a: f"Fecho o {a['nome']}?",
         params={"type": "object", "properties": {"nome": {"type": "string"}}, "required": ["nome"]})

    def create(**kw):
        call = SimpleNamespace(id="c1", function=SimpleNamespace(name="fechar_programa", arguments='{"nome": "Chrome"}'))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))])

    monkeypatch.setattr(llm.settings, "GROQ_API_KEY", "chave-teste")
    monkeypatch.setattr(llm, "_client", lambda *a, **k: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    assert run(llm.generate_jarvis_response("fecha o chrome")) == "Fecho o Chrome?"
    assert done == [] and session.pending_action["kind"] == "skill"


# ------------------------------------------------------------------ rotas e conversa
@pytest.fixture
def client(isolated_data, monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from core import speech

    async def fake_speak(text, release_busy=True, idle_after=True):
        session.busy = False if release_busy else session.busy

    monkeypatch.setattr(speech, "speak", fake_speak)
    access.reset_for_tests(access.UNLOCKED)
    session.busy = False
    return TestClient(main.app)


def test_chat_answers_through_a_skill_without_ai(client, monkeypatch):
    from services import llm_orchestrator as llm

    async def no_ai(*a, **k):
        raise AssertionError("não devia chamar a IA")

    monkeypatch.setattr("core.turns.generate_jarvis_response", no_ai)
    monkeypatch.setattr(llm, "generate_jarvis_response", no_ai)

    async def placar(ctx):
        return SkillResult(speech="Três a um, senhor.", cards=[{"type": "placar_teste"}])

    _add(placar, triggers=[r"\bplacar de teste\b"])
    started = time.monotonic()
    r = client.post("/api/chat", json={"message": "Jarvis, qual o placar de teste?"})
    assert r.status_code == 200
    assert r.json()["response"] == "Três a um, senhor."
    assert {"type": "placar_teste"} in r.json()["cards"]
    assert time.monotonic() - started < 2


def test_skill_routes(client):
    async def eco(ctx, texto: str):
        return SkillResult(speech=texto)

    _add(eco, params={"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]})
    items = client.get("/api/skills").json()["items"]
    assert [i["name"] for i in items] == ["eco"] and items[0]["enabled"] is True
    assert client.post("/api/skills/eco/run", json={"args": {"texto": "olá"}}).json()["speech"] == "olá"
    assert client.post("/api/skills/eco/toggle", json={"enabled": False}).json()["enabled"] is False
    assert client.get("/api/skills").json()["items"][0]["enabled"] is False
    assert client.post("/api/skills/nao_existe/toggle", json={"enabled": True}).status_code == 404


def test_skill_routes_need_unlock(client, credentials):
    access.reset_for_tests(access.LOCKED)
    assert client.get("/api/skills").status_code == 403
