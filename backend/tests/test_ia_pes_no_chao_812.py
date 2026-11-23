# V8.12: IA com os pés no chão (menos alucinação): pesquisa para fato atual, regras e temperatura baixa.
import pytest

from services import grounding
from services import llm_orchestrator as llm


@pytest.mark.parametrize("frase", [
    "quais as notícias da DC",
    "quem é o técnico do Palmeiras",
    "qual a cotação do dólar hoje",
    "qual a inflação atual",
    "quando sai o próximo filme do Batman",
    "quanto custa o iPhone 17",
    "Jarvis, qual o último lançamento da Apple",
    "o Ozzy ainda está vivo",
    "você sabe quem é o presidente do Brasil",
])
def test_fato_atual_vai_para_a_pesquisa(frase):
    assert grounding.needs_fresh_facts(frase)


@pytest.mark.parametrize("frase", [
    "o que é inflação",            # conceito, não dado
    "como funciona a fotossíntese",
    "qual a capital da França",
    "toca a última do Coldplay",   # ação: com pesquisa a IA não usaria as Skills
    "Jarvis, abre as notícias",
    "o que eu tenho hoje",          # agenda do usuário, não internet
    "meus lembretes de hoje",
    "me conta uma piada",
    "oi tudo bem",
])
def test_o_resto_nao_pesquisa(frase):
    assert not grounding.needs_fresh_facts(frase)


def test_regras_de_veracidade_no_prompt_de_todas_as_ias():
    assert grounding.RULES in llm.SYSTEM_PROMPT
    assert "nunca invente" in llm.SYSTEM_PROMPT


def _prompt(monkeypatch, text, web):
    monkeypatch.setattr(llm, "get_name", lambda: "")
    monkeypatch.setattr(llm, "get_about", lambda: "")
    monkeypatch.setattr(llm.memory, "prompt_context", lambda: "")
    return llm._build_prompt(text, routine=False, frame=False, camera_asked=False, news=[], news_asked=False, web=web)


def test_nota_do_pedido(monkeypatch):
    assert grounding.WEB_NOTE in _prompt(monkeypatch, "quem é o técnico do Palmeiras", web=True)
    # fato atual sem pesquisa: avisa e oferece, em vez de chutar
    assert grounding.NO_SEARCH_NOTE in _prompt(monkeypatch, "quem é o técnico do Palmeiras", web=False)
    # conversa comum: nada a mais
    p = _prompt(monkeypatch, "me conta uma piada", web=False)
    assert grounding.NO_SEARCH_NOTE not in p and grounding.WEB_NOTE not in p


def test_ia_sem_pesquisa_nao_finge_que_pesquisou(monkeypatch):
    seen = {}

    def fake_groq(prompt, frame, history):
        seen["prompt"] = prompt
        return "ok"

    monkeypatch.setattr(llm, "_call_groq", fake_groq)
    llm._call_one("groq", f"{grounding.WEB_NOTE}\nMensagem", None, [], deep=True)
    assert grounding.NO_SEARCH_NOTE in seen["prompt"]
    assert grounding.WEB_NOTE not in seen["prompt"]


def test_temperatura_baixa_e_reserva_sem_ela(monkeypatch):
    calls = []

    def create(**kw):
        calls.append(kw)
        if "temperature" in kw:
            raise ValueError("Unsupported parameter: 'temperature' is not supported with this model.")
        return "resposta"

    assert llm._with_temperature(create, model="o3") == "resposta"
    assert calls[0]["temperature"] == pytest.approx(0.3)
    assert "temperature" not in calls[1]

    def broken(**kw):
        raise RuntimeError("sem internet")

    with pytest.raises(RuntimeError):  # outro erro não é engolido
        llm._with_temperature(broken)


def test_temperatura_do_env(monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_TEMPERATURE", 5, raising=False)
    assert llm._temperature() == 1.0
    monkeypatch.setattr(llm.settings, "LLM_TEMPERATURE", "x", raising=False)
    assert llm._temperature() == 0.3
