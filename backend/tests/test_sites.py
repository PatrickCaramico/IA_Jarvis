import asyncio
import json

import pytest

from modules import tools


def test_load_shortcuts_supports_object_entries(tmp_path, monkeypatch):
    shortcuts = tmp_path / "atalhos.json"
    monkeypatch.setattr(tools, "_SHORTCUTS_PATH", shortcuts)
    shortcuts.write_text(
        json.dumps({
            "gmail": {"url": "https://mail.google.com", "apelidos": ["email", "correio"], "janela_app": False},
            "notion": {"url": "https://www.notion.so", "apelidos": ["bloco"], "janela_app": True},
        }),
        encoding="utf-8",
    )

    data = tools._load_shortcuts()

    assert data["gmail"]["url"] == "https://mail.google.com"
    assert data["notion"]["janela_app"] is True


def test_load_shortcuts_uses_example_when_profile_file_is_missing(tmp_path, monkeypatch):
    shortcuts = tmp_path / "atalhos.json"
    example = tmp_path / "atalhos.example.json"
    expected = {"projetos": "https://example.com/projects"}
    example.write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(tools, "_SHORTCUTS_PATH", shortcuts)
    monkeypatch.setattr(tools, "_SHORTCUTS_EXAMPLE_PATH", example, raising=False)

    assert tools._load_shortcuts() == expected
    assert not shortcuts.exists()


def test_validate_site_url_rejects_dangerous_urls():
    with pytest.raises(ValueError):
        tools.validate_site_url("javascript:alert(1)")

    with pytest.raises(ValueError):
        tools.validate_site_url("file:///C:/Windows/System32/drivers/etc/hosts")


def test_h_open_prefers_spotify_desktop_when_site_exists(tmp_path, monkeypatch):
    shortcuts = tmp_path / "atalhos.json"
    shortcuts.write_text(json.dumps({"spotify": "https://open.spotify.com"}), encoding="utf-8")
    monkeypatch.setattr(tools, "_SHORTCUTS_PATH", shortcuts)
    opened = []
    monkeypatch.setattr(tools, "_open_spotify_desktop", lambda: opened.append("desktop"))
    monkeypatch.setattr(tools, "_open_site", lambda site: opened.append("site"))

    reply = asyncio.run(tools._h_open("abre o Spotify", "abre o spotify", 3, ""))

    assert reply == "Spotify aberto no aplicativo do computador, senhor."
    assert opened == ["desktop"]


def test_open_site_uses_default_browser_when_chrome_is_missing(monkeypatch):
    opened = []
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)
    monkeypatch.setattr(tools.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(tools.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Chrome não existe"))
    monkeypatch.setattr(tools, "_open_in_default_browser", opened.append)

    tools._open_site({"url": "https://example.com", "janela_app": True})

    assert opened == ["https://example.com"]
