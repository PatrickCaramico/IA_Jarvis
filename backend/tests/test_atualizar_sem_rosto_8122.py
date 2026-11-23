# V8.12.2: depois da atualização, a central volta liberada (antes reiniciava bloqueada e pedia o rosto de novo).
from modules import access


def test_liberada_antes_liberada_depois():
    access.reset_for_tests(access.UNLOCKED)
    assert access.remember_for_restart(now=1000.0)
    access.reset_for_tests(access.LOCKED)  # o reinício: o estado volta ao padrão (bloqueado)
    assert access.resume_after_restart(now=1060.0)
    assert access.get_state() == access.UNLOCKED
    # a marca vale uma vez só
    access.reset_for_tests(access.LOCKED)
    assert not access.resume_after_restart(now=1070.0)
    assert access.get_state() == access.LOCKED


def test_bloqueada_continua_bloqueada():
    access.reset_for_tests(access.LOCKED)
    assert not access.remember_for_restart(now=1000.0)
    assert not access.resume_after_restart(now=1010.0)
    assert access.get_state() == access.LOCKED


def test_marca_velha_nao_libera():
    access.reset_for_tests(access.UNLOCKED)
    access.remember_for_restart(now=1000.0)
    access.reset_for_tests(access.LOCKED)
    assert not access.resume_after_restart(now=1000.0 + access.RESUME_TTL_S + 1)
    assert access.get_state() == access.LOCKED


def test_bloquear_apaga_a_marca():
    access.reset_for_tests(access.UNLOCKED)
    access.remember_for_restart(now=1000.0)
    access.lock("manual")  # bloqueou depois de mandar atualizar
    assert not access.resume_after_restart(now=1010.0)
    assert access.get_state() == access.LOCKED


def test_marca_estragada_nao_libera():
    access.reset_for_tests(access.LOCKED)
    access._RESUME_PATH.write_text("{quebrado", encoding="utf-8")
    assert not access.resume_after_restart(now=1000.0)
    assert not access._RESUME_PATH.exists()
    assert access.get_state() == access.LOCKED


# V8.12.2: tela de atualização com o número da versão nova e os destaques do CHANGELOG baixado
def test_destaques_do_changelog():
    from modules import self_update

    text = (
        "# Changelog\n\n## 8.12.2 — 23 de novembro de 2026\n\n**⟳ Atualizar sem pedir o rosto**\n- detalhe\n\n"
        "**🎵 Spotify no site**\n- outro\n\n## 8.12.1 — 22 de novembro\n\n**Antiga**\n"
    )
    assert self_update.changelog_highlights(text, "8.12.2") == ["⟳ Atualizar sem pedir o rosto", "🎵 Spotify no site"]
    assert self_update.changelog_highlights(text, "8.12.1") == ["Antiga"]
    assert self_update.changelog_highlights(text, "9.9.9") == ["⟳ Atualizar sem pedir o rosto", "🎵 Spotify no site"]  # a de cima
    assert self_update.changelog_highlights("", "8.12.2") == []


def test_o_changelog_real_tem_destaques_da_versao_atual():
    from modules import self_update
    from version import VERSION

    text = (self_update.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert self_update.changelog_highlights(text, VERSION), "a seção da versão atual precisa de títulos em **negrito**"


def test_musica_do_pc_para_a_nuvem(monkeypatch):
    from modules import cloud_sync, spotify

    monkeypatch.setattr(spotify, "configured", lambda: True)
    monkeypatch.setattr(spotify, "connected", lambda: True)
    monkeypatch.setattr(spotify, "now_playing", lambda: {"state": "playing", "title": "Yellow", "artist": "Coldplay",
                                                          "image": None, "progress_ms": 1, "duration_ms": 2, "extra": "x"})
    out = cloud_sync._now_playing()
    assert out["title"] == "Yellow" and out["state"] == "playing" and "extra" not in out and out["at"] > 0
    monkeypatch.setattr(spotify, "now_playing", lambda: (_ for _ in ()).throw(RuntimeError("sem internet")))
    assert cloud_sync._now_playing()["state"] == "error"
    monkeypatch.setattr(spotify, "connected", lambda: False)
    assert cloud_sync._now_playing()["state"] == "off"
