"""V8.13: streaming da IA para o chat (Groq/OpenAI, Claude e Gemini), canal seguro entre threads e turno."""
import asyncio
import threading
from types import SimpleNamespace as NS

import pytest

from services import llm_orchestrator as llm
from services import llm_stream


# ------------------------------------------------------------------ canal
def _sink(events, interval=0.0):
    loop = asyncio.new_event_loop()
    sink = llm_stream.StreamSink(loop, events.append, min_interval=interval)
    return loop, sink


def _drain(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()


def test_sink_sends_accumulated_text_in_order():
    events = []
    loop, sink = _sink(events)
    sink.claim()
    sink.delta("Olá")
    sink.delta(", senhor")
    sink.delta("")
    _drain(loop)
    assert [e["text"] for e in events] == ["Olá", "Olá, senhor"]
    assert [e["seq"] for e in events] == [1, 2]
    loop.close()


def test_sink_throttles_and_resets():
    events = []
    loop, sink = _sink(events, interval=60)
    sink.claim()
    sink.delta("a")  # primeiro passa
    sink.delta("b")  # segurado (menos de 60 s)
    sink.begin()  # outra IA: recomeça
    _drain(loop)
    assert events[0]["text"] == "a"
    assert events[-1] == {"type": "response_stream", "seq": 2, "text": "", "reset": True}
    loop.close()


def test_sink_ignores_other_threads_and_after_close():
    events = []
    loop, sink = _sink(events)
    sink.claim()
    other = threading.Thread(target=lambda: sink.delta("da skill"))
    other.start()
    other.join()
    sink.close()
    sink.delta("atrasado")
    _drain(loop)
    assert events == []
    loop.close()


def test_current_only_for_the_owner_thread():
    events = []
    loop, sink = _sink(events)
    token = llm_stream.use(sink)
    try:
        assert llm_stream.current() is None  # ainda sem dona
        sink.claim()
        assert llm_stream.current() is sink
    finally:
        llm_stream.reset(token)
        loop.close()


# ------------------------------------------------------------------ IAs falsas
def _chunk(content=None, tool_calls=None):
    return NS(choices=[NS(delta=NS(content=content, tool_calls=tool_calls))])


class FakeOpenAI:
    def __init__(self, streams, plain=None):
        self.streams, self.plain, self.calls = list(streams), plain, []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        if kw.get("stream"):
            return iter(self.streams.pop(0))
        return self.plain


@pytest.fixture
def streaming(monkeypatch):
    events = []
    loop = asyncio.new_event_loop()
    sink = llm_stream.StreamSink(loop, events.append, min_interval=0)
    sink.claim()
    token = llm_stream.use(sink)
    yield events, loop
    llm_stream.reset(token)
    loop.close()


def test_openai_style_streams_plain_answer(streaming):
    events, loop = streaming
    client = FakeOpenAI([[_chunk("São "), _chunk("10 horas"), NS(choices=[])]])
    assert llm._openai_style(client, "m", [{"role": "user", "content": "hora"}], None) == "São 10 horas"
    assert client.calls[0]["stream"] is True
    _drain(loop)
    assert events[-1]["text"] == "São 10 horas"


def test_openai_style_rebuilds_tool_calls_and_streams_the_follow_up(streaming, monkeypatch):
    events, loop = streaming
    tc1 = NS(index=0, id="c1", function=NS(name="converter_unidades", arguments='{"valor": '))
    tc2 = NS(index=0, id=None, function=NS(name=None, arguments='5}'))
    client = FakeOpenAI([[_chunk(tool_calls=[tc1]), _chunk(tool_calls=[tc2])],
                         [_chunk("Cinco milhas "), _chunk("são 8 km.")]])
    ran = []

    class TS:
        skills = ["x"]

        def run(self, name, args):
            ran.append((name, args))
            return NS(ok=True, speech="", data={"km": 8}, pending=False, cards=[])

    monkeypatch.setattr("core.skills.llm_adapters.to_openai", lambda skills: [])
    out = llm._openai_style(client, "m", [{"role": "user", "content": "5 milhas"}], TS())
    assert ran == [("converter_unidades", {"valor": 5})]
    assert out == "Cinco milhas são 8 km."
    follow = client.calls[1]["messages"]
    assert follow[-1]["role"] == "tool" and follow[-2]["tool_calls"][0]["function"]["arguments"] == '{"valor": 5}'
    _drain(loop)
    assert events[-1]["text"] == "Cinco milhas são 8 km."


def test_without_sink_it_calls_once_without_stream():
    plain = NS(choices=[NS(message=NS(content=" Pronto. ", tool_calls=None))])
    client = FakeOpenAI([], plain=plain)
    assert llm._openai_style(client, "m", [], None) == "Pronto."
    assert "stream" not in client.calls[0]


def test_anthropic_streams_and_retries_without_temperature(streaming):
    events, loop = streaming
    tries = []

    class Stream:
        def __init__(self, kw):
            self.kw = kw

        def __enter__(self):
            if "temperature" in self.kw:
                raise RuntimeError("temperature is not supported")
            return NS(text_stream=iter(["Boa ", "noite."]))

        def __exit__(self, *a):
            return False

    client = NS(messages=NS(stream=lambda **kw: (tries.append(kw), Stream(kw))[1]))
    out = llm._anthropic_stream(client, llm_stream.current(), {"model": "x", "max_tokens": 10, "system": "s", "messages": []})
    assert out == "Boa noite." and len(tries) == 2
    _drain(loop)
    assert events[-1]["text"] == "Boa noite."


def test_gemini_stream_is_merged_like_a_normal_response(streaming):
    events, loop = streaming
    gm = NS(web_search_queries=["clima"], grounding_chunks=[])
    chunks = [
        NS(candidates=[NS(grounding_metadata=None, content=NS(parts=[NS(text="pensando", thought=True, function_call=None)]))]),
        NS(candidates=[NS(grounding_metadata=None, content=NS(parts=[NS(text="Vai chover ", thought=False, function_call=None)]))]),
        NS(candidates=[NS(grounding_metadata=gm, content=NS(parts=[NS(text="à tarde.", thought=False, function_call=None)]))]),
    ]

    class Models:
        def generate_content_stream(self, **kw):
            return iter(chunks)

    pytest.importorskip("google.genai")
    from google.genai import types

    real = types.Content
    types.Content = lambda role, parts: NS(role=role, parts=parts)  # as partes falsas não passam na validação
    try:
        resp = llm._gemini_generate(NS(models=Models()), model="m", contents=[], config=None)
    finally:
        types.Content = real
    assert resp.text == "Vai chover à tarde." and resp.function_calls is None
    assert resp.candidates[0].grounding_metadata is gm
    _drain(loop)
    assert events[-1]["text"] == "Vai chover à tarde."  # o "pensamento" não vai para a tela


# ------------------------------------------------------------------ turno inteiro
def test_generate_response_streams_and_closes(monkeypatch):
    events = []

    def fake_llm(prompt, frame, history, deep):
        sink = llm_stream.current()
        assert sink is not None
        sink.delta("Resposta ")
        sink.delta("completa.")
        return "Resposta completa."

    monkeypatch.setattr(llm, "_call_llm", fake_llm)
    monkeypatch.setattr(llm, "_tool_session", lambda *a, **k: None)
    monkeypatch.setattr(llm_stream, "MIN_INTERVAL_S", 0)

    async def scenario():
        text = await llm.generate_jarvis_response("conte algo", on_stream=events.append)
        await asyncio.sleep(0)
        return text

    assert asyncio.run(scenario()) == "Resposta completa."
    assert events and events[-1]["text"].startswith("Resposta")


def test_routine_does_not_stream(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "_call_llm", lambda *a: seen.append(llm_stream.current()) or "ok")
    monkeypatch.setattr(llm, "_tool_session", lambda *a, **k: None)
    monkeypatch.setattr(llm, "fetch_top_news", lambda: [])
    monkeypatch.setattr(llm, "capture_webcam_frame", lambda: None)
    asyncio.run(llm.generate_jarvis_response("bom dia", routine=True, on_stream=lambda e: None))
    assert seen == [None]
