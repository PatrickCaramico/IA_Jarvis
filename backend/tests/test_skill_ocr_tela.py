"""V9.0: ler o texto da tela/imagem offline (OCR do Windows). PowerShell e área de transferência são falsos."""
import asyncio
from pathlib import Path

import pytest

import skills.ocr_tela as oc
from core.skills import registry, router
from modules.quick_replies import _norm


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def ask(phrase):
    return asyncio.run(router.try_fast_path(phrase))


def test_phrases(real_skills):
    for phrase, fonte in [("copia o texto da tela", "tela"), ("pega o texto dessa janela", "tela"), ("extrai o texto da tela", "tela"),
                          ("o que está escrito na tela?", "tela"), ("copia o texto da imagem que eu copiei", "imagem"),
                          ("le o texto do print que eu copiei", "imagem")]:
        hit = match(phrase)
        assert hit and hit[0].name == "ler_texto_da_tela" and hit[1] == {"fonte": fonte}, phrase
    for phrase in ("leia a tela", "explica a tela", "tira um print", "bloqueia a tela", "o que e isso na tela"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "ler_texto_da_tela", phrase


@pytest.fixture
def windows(monkeypatch, tmp_path):
    img = tmp_path / "tela.png"
    img.write_bytes(b"png")
    state = {"ocr": "Fatura de novembro\n  Total:   R$ 120,00  \n\nVencimento 10/12", "clip": img, "copied": []}
    monkeypatch.setattr(oc, "capture_screen", lambda: img)
    monkeypatch.setattr(oc, "clipboard_image", lambda: state["clip"])
    monkeypatch.setattr(oc, "_ps", lambda script, image, sta=False: state["ocr"])
    monkeypatch.setattr("skills.clipboard_ai.write_clipboard", lambda t: state["copied"].append(t) or True)
    monkeypatch.setattr(oc, "os", type("FakeOs", (), {"name": "nt", "environ": {}, "getpid": staticmethod(lambda: 1)}))
    return state, img


def test_reads_copies_and_cleans_up(real_skills, windows):
    state, img = windows
    res = ask("copia o texto da tela")
    assert res.speech.startswith("Copiei 3 linhas de texto, é só colar. Começa com: Fatura de novembro")
    assert state["copied"] == ["Fatura de novembro\nTotal: R$ 120,00\nVencimento 10/12"]
    assert res.cards[0]["data"]["tag"] == "TEXTO DA TELA"
    assert not img.exists()  # a imagem temporária some


def test_no_text_no_image_no_engine(real_skills, windows):
    state, _ = windows
    state["ocr"] = "   \n"
    Path(state["clip"]).write_bytes(b"x")
    assert ask("copia o texto da imagem que eu copiei").speech == "Não achei texto legível na imagem, senhor."
    state["clip"] = None
    assert "Não tem imagem na área de transferência" in ask("copia o texto da imagem que eu copiei").speech
    state["ocr"] = "##SEM_OCR##"
    assert "não está instalado" in ask("copia o texto da tela").speech


def test_powershell_failure_is_honest(real_skills, windows, monkeypatch):
    def boom(script, image, sta=False):
        raise RuntimeError("erro do PowerShell")

    monkeypatch.setattr(oc, "_ps", boom)
    assert ask("copia o texto da tela").speech == "Não consegui ler o texto agora, senhor. O detalhe ficou no log."


def test_scripts_pass_the_path_by_environment():
    assert "$env:JARVIS_IMG" in oc.OCR_SCRIPT and "$env:JARVIS_IMG" in oc.CLIP_IMAGE_SCRIPT
    assert "Windows.Media.Ocr.OcrEngine" in oc.OCR_SCRIPT
