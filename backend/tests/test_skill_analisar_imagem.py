"""V9.4: "analisa essa imagem" — a imagem copiada ou a mais nova salva, mandada para a IA de visão."""
import asyncio
import os
import time

import cv2
import numpy as np
import pytest

from core import runtime
from core.skills import registry, router
from modules.quick_replies import _norm
from services import llm_orchestrator
from skills import analisar_imagem as ai


def match(phrase):
    return registry.match(_norm(phrase), phrase)


def _jpg() -> bytes:
    img = np.full((60, 80, 3), 200, np.uint8)
    return cv2.imencode(".jpg", img)[1].tobytes()


def test_phrases(real_skills):
    for phrase in ("analisa essa imagem", "o que tem nessa foto?", "analisa o print que eu tirei", "analisa a imagem que eu copiei",
                   "descreve essa imagem", "analisa a última foto", "le essa imagem pra mim"):
        hit = match(phrase)
        assert hit and hit[0].name == "analisar_imagem", phrase
    # câmera, tela, texto (OCR), print e o PC têm caminhos próprios
    for phrase in ("analisa esse item na câmera", "copia o texto da imagem que eu copiei", "tira um print", "analisa o meu PC",
                   "o que é isso na tela", "manda a foto pro whatsapp"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "analisar_imagem", phrase


def test_newest_image_only_recent_images(tmp_path):
    now = time.time()
    old = tmp_path / "velha.png"
    old.write_bytes(b"x")
    os.utime(old, (now - 3 * 3600, now - 3 * 3600))
    (tmp_path / "nota.txt").write_text("x")
    new = tmp_path / "print.png"
    new.write_bytes(b"x")
    os.utime(new, (now - 60, now - 60))
    assert ai.newest_image([tmp_path, tmp_path / "nao_existe"], now=now) == new
    os.utime(new, (now - 3 * 3600, now - 3 * 3600))
    assert ai.newest_image([tmp_path], now=now) is None


def test_speech_is_short_and_clean():
    assert ai.short_speech("**É um gato.** Ele está dormindo. Parece um siamês.") == "É um gato. Ele está dormindo."


@pytest.fixture
def sent(monkeypatch):
    got = []

    async def fake_broadcast(e):
        got.append(e)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    return got


def test_analyzes_the_copied_image(real_skills, sent, monkeypatch):
    asked = []
    monkeypatch.setattr(ai, "clipboard_image", lambda: (_jpg(), "a imagem copiada"))
    monkeypatch.setattr(llm_orchestrator, "ask_with_image",
                        lambda prompt, image: asked.append((prompt, image)) or "É um gráfico de vendas. Subiu 20% em março. Detalhes...")
    res = asyncio.run(router.try_fast_path("analisa essa imagem"))
    assert res.ok and res.speech == "É um gráfico de vendas. Subiu 20% em março."
    assert res.cards[0]["data"]["tag"] == "ANÁLISE DA IMAGEM" and res.cards[0]["data"]["source"] == "a imagem copiada"
    prompt, image = asked[0]
    assert "a imagem copiada" in prompt and '"analisa essa imagem"' in prompt and image
    assert [e["status"] for e in sent if e.get("type") == "agent"] == ["working", "done"]


def test_falls_back_to_newest_file_then_explains(real_skills, sent, monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "clipboard_image", lambda: (None, ""))
    pic = tmp_path / "Captura.png"
    pic.write_bytes(_jpg())
    monkeypatch.setattr(ai, "newest_image", lambda: pic)
    monkeypatch.setattr(llm_orchestrator, "ask_with_image", lambda prompt, image: "Uma tela de erro do Windows.")
    res = asyncio.run(router.try_fast_path("o que tem nessa imagem?"))
    assert res.speech == "Uma tela de erro do Windows." and res.cards[0]["data"]["source"] == "a imagem Captura.png"

    monkeypatch.setattr(ai, "newest_image", lambda: None)
    res = asyncio.run(router.try_fast_path("analisa essa imagem"))
    assert not res.ok and "Control C" in res.speech


def test_ai_error_is_honest(real_skills, sent, monkeypatch):
    monkeypatch.setattr(ai, "clipboard_image", lambda: (_jpg(), "a imagem copiada"))

    def boom(prompt, image):
        raise RuntimeError("sem chave")

    monkeypatch.setattr(llm_orchestrator, "ask_with_image", boom)
    res = asyncio.run(router.try_fast_path("analisa essa imagem"))
    assert not res.ok and "a IA não respondeu" in res.speech
    monkeypatch.setattr(ai, "clipboard_image", lambda: (b"nao e imagem", "a imagem copiada"))
    res = asyncio.run(router.try_fast_path("analisa essa imagem"))
    assert not res.ok and "não consegui abri-la" in res.speech
