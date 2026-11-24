"""V9.4: tela de bloqueio por voz (widgets fixos com animação) e o avatar holográfico feito da foto do rosto."""
import asyncio

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import main
from core import runtime
from core.skills import registry, router
from modules import access, face, holo_avatar, prefs
from modules.quick_replies import _norm
from skills import tela_de_bloqueio as tb


def match(phrase):
    return registry.match(_norm(phrase), phrase)


@pytest.fixture
def sent(monkeypatch):
    got = []

    async def fake_broadcast(e):
        got.append(e)

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    return got


def test_phrases(real_skills):
    for phrase, args in [
        ("deixa o clima sempre aparecer na tela de bloqueio", {"widgets": ["weather"], "acao": "mostrar"}),
        ("coloca o clima e a água na tela de bloqueio", {"widgets": ["weather", "water"], "acao": "mostrar"}),
        ("mostra o relógio no bloqueio", {"widgets": ["clock"], "acao": "mostrar"}),
        ("tira a água da tela de bloqueio", {"widgets": ["water"], "acao": "tirar"}),
        ("coloca meu avatar na tela de bloqueio", {"widgets": ["avatar"], "acao": "mostrar"}),
        ("não quero o spotify na tela de bloqueio", {"widgets": ["spotify"], "acao": "tirar"}),
    ]:
        hit = match(phrase)
        assert hit and hit[0].name == "widgets_do_bloqueio" and hit[1] == args, phrase
    for phrase in ("como está o clima", "bloqueia a tela", "modo bloqueio", "tira um print da tela", "mostra a água"):
        hit = match(phrase)
        assert hit is None or hit[0].name != "widgets_do_bloqueio", phrase


def test_apply_is_pure():
    cards, avatar, changed, same = tb.apply(["clock"], False, ["weather", "clock", "avatar"], True)
    assert cards == ["clock", "weather"] and avatar is True and changed == ["weather", "avatar"] and same == ["clock"]
    cards, avatar, changed, same = tb.apply(cards, avatar, ["weather", "water"], False)
    assert cards == ["clock"] and changed == ["weather"] and same == ["water"]


def test_show_and_hide_updates_lock_screen_now(real_skills, sent, monkeypatch):
    prefs.update(lock_cards=["clock"])
    res = asyncio.run(router.try_fast_path("deixa o clima sempre aparecer na tela de bloqueio"))
    assert res.speech == "Pronto, senhor: o clima fica sempre na tela de bloqueio. O clima entra com a animação do tempo de agora."
    assert prefs.get_all()["lock_cards"] == ["clock", "weather"]
    assert sent[-1] == {"type": "prefs_updated", "lock_cards": ["clock", "weather"], "lock_avatar_enabled": False,
                        "lock_cards_new": ["weather"]}
    again = asyncio.run(router.try_fast_path("coloca o clima na tela de bloqueio"))
    assert again.speech == "O clima já está na tela de bloqueio, senhor."
    off = asyncio.run(router.try_fast_path("tira o clima e o relógio da tela de bloqueio"))
    assert off.speech == "Pronto, senhor: tirei o clima e o relógio da tela de bloqueio." and prefs.get_all()["lock_cards"] == []


def test_avatar_needs_a_face(real_skills, sent, monkeypatch):
    monkeypatch.setattr(face, "has_profile", lambda: False)
    res = asyncio.run(router.try_fast_path("coloca meu avatar na tela de bloqueio"))
    assert not res.ok and "foto do seu rosto" in res.speech and not prefs.get_all()["lock_avatar_enabled"]
    monkeypatch.setattr(face, "has_profile", lambda: True)
    res = asyncio.run(router.try_fast_path("coloca meu avatar na tela de bloqueio"))
    assert res.speech == "Pronto, senhor: o seu avatar fica sempre na tela de bloqueio." and prefs.get_all()["lock_avatar_enabled"]


# ------------------------------------------------------------------ o avatar holográfico
def _photo(tmp_path):
    img = np.full((480, 640, 3), 90, np.uint8)
    cv2.circle(img, (320, 220), 110, (200, 180, 160), -1)  # um "rosto"
    cv2.circle(img, (280, 200), 12, (30, 30, 30), -1)
    cv2.circle(img, (360, 200), 12, (30, 30, 30), -1)
    path = tmp_path / "profile.jpg"
    ok, buf = cv2.imencode(".jpg", img)
    path.write_bytes(buf.tobytes())
    return path


def test_crop_square_keeps_inside_the_photo():
    assert holo_avatar.crop_square(640, 480, None) == (104, 0, 432)
    x, y, side = holo_avatar.crop_square(640, 480, (500, 10, 120, 140))  # rosto no canto: não sai da foto
    assert x + side <= 640 and y >= 0 and side <= 480


def test_render_and_cache(tmp_path, monkeypatch):
    src = _photo(tmp_path)
    monkeypatch.setattr(holo_avatar, "_face_box", lambda img: (210, 110, 220, 220))
    png = holo_avatar.render(src.read_bytes())
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    assert img.shape == (holo_avatar.SIZE, holo_avatar.SIZE, 4)
    assert img[0, 0, 3] == 0 and img[holo_avatar.SIZE // 2, holo_avatar.SIZE // 2, 3] > 0  # cantos somem, centro aparece
    b, g, r = (int(v) for v in img[holo_avatar.SIZE // 2, holo_avatar.SIZE // 2, :3])
    assert b >= r and g >= r  # ciano, não a cor da foto
    with pytest.raises(ValueError):
        holo_avatar.render(b"nada")

    monkeypatch.setattr(face, "PHOTO_PATH", src)
    out = holo_avatar.ensure()
    assert out and out.exists()
    calls = []
    monkeypatch.setattr(holo_avatar, "render", lambda data: calls.append(1) or b"png")
    assert holo_avatar.ensure() == out and calls == []  # foto não mudou: usa o salvo


def test_avatar_route_only_when_enabled(isolated_data, tmp_path, monkeypatch):
    monkeypatch.setattr(face, "PHOTO_PATH", _photo(tmp_path))
    monkeypatch.setattr(holo_avatar, "_face_box", lambda img: None)
    access.reset_for_tests(access.LOCKED)
    assert access.is_allowed("GET", "/api/lock/avatar", access.LOCKED)
    client = TestClient(main.app)
    assert client.get("/api/lock/avatar").status_code == 404
    prefs.update(lock_avatar_enabled=True)
    r = client.get("/api/lock/avatar")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "lock_avatar_enabled" in prefs.PUBLIC_KEYS
