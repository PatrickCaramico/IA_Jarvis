"""V9.0: copiar e colar por voz (histórico de copiados): ler, copiar de novo, fixar e limpar com "sim"."""
import asyncio

import pytest

import skills.copiados as cp
from core import confirm
from core.skills import registry, router
from modules import desk
from modules.quick_replies import _norm


@pytest.fixture
def clipboard(monkeypatch):
    written = []
    monkeypatch.setattr("skills.clipboard_ai.write_clipboard", lambda t: written.append(t) or True)
    for t in ["Rua das Acácias, 123 - Maceió", "fulano@exemplo.com", "https://www.booking.com/hotel/br/xyz.html",
              "(82) 99999-1234", "texto qualquer"]:
        desk.clip_add(t)
    return written


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def ask(phrase):
    return asyncio.run(router.try_fast_path(phrase))


def test_phrases(real_skills):
    cases = {
        "o que eu copiei?": {"acao": "ler"},
        "qual foi a ultima coisa que eu copiei": {"acao": "ler"},
        "copia de novo o ultimo link": {"acao": "copiar", "qual": "link"},
        "copia de novo o penultimo": {"acao": "copiar", "qual": "penultimo"},
        "cola o e-mail que eu copiei": {"acao": "copiar", "qual": "email"},
        "copia de novo o endereco": {"acao": "copiar", "qual": "endereco"},
        "me da o telefone que eu copiei": {"acao": "copiar", "qual": "numero"},
        "fixa o ultimo copiado": {"acao": "fixar"},
    }
    for phrase, args in cases.items():
        hit = match(phrase)
        assert hit and hit[0].name == "copiados" and hit[1] == args, phrase
    assert match("apaga os copiados")[0].name == "limpar_copiados"
    for phrase in ("resume o que eu copiei", "traduz o que eu copiei", "o que eu copiei sobre o hotel", "copia esse arquivo"):
        hit = match(phrase)
        assert hit is None or hit[0].name not in ("copiados", "limpar_copiados"), phrase


def test_read_and_copy_again(real_skills, clipboard):
    res = ask("o que eu copiei?")
    assert res.speech == "A última coisa que o senhor copiou foi texto qualquer"
    assert len(res.cards[0]["data"]["rows"]) == 5
    assert "booking.com" in ask("copia de novo o último link").speech
    assert clipboard[-1] == "https://www.booking.com/hotel/br/xyz.html"
    ask("copia de novo o e-mail")
    assert clipboard[-1] == "fulano@exemplo.com"
    ask("copia de novo o endereço")
    assert clipboard[-1].startswith("Rua das Acácias")
    ask("copia de novo o penúltimo")
    assert clipboard[-1] == "(82) 99999-1234"


def test_pin_survives_limit_and_clear(real_skills, clipboard, monkeypatch):
    ask("fixa o último copiado")
    assert desk.clips()["itens"][0].get("fixado") is True
    monkeypatch.setattr(desk, "MAX_CLIPS", 3)
    for i in range(10):
        desk.clip_add(f"novo item {i}")
    texts = [i["texto"] for i in desk.clips()["itens"]]
    assert "texto qualquer" in texts and len(texts) == 4  # 3 + o fixado
    res = ask("apaga os copiados")
    assert res.pending and "Diga sim" in res.speech
    assert len(desk.clips()["itens"]) == 4  # ainda não apagou
    out = asyncio.run(confirm.answer("sim"))
    assert "Ficaram os 1 fixados" in out
    assert [i["texto"] for i in desk.clips()["itens"]] == ["texto qualquer"]


def test_empty_and_missing(real_skills, monkeypatch):
    monkeypatch.setattr("skills.clipboard_ai.write_clipboard", lambda t: True)
    assert "Ainda não tenho nada" in ask("o que eu copiei?").speech
    desk.clip_add("só um texto")
    assert ask("copia de novo o último link").speech == "Não achei nenhum link nos copiados, senhor."


def test_describe():
    assert cp.describe("https://www.youtube.com/watch?v=1") == "um link do site youtube.com"
    assert cp.describe("a" * 200).endswith("…")
