"""V6.5.11: "abra o YouTube" pergunta em qual navegador."""
from modules import browser_choice as bc
from modules import browser_window as bw


def test_parse_answers():
    assert bc.parse("no Chrome") == ("chrome", False)
    assert bc.parse("Jarvis, abre no Edge") == ("edge", False)
    assert bc.parse("sempre no Google Chrome") == ("chrome", True)
    assert bc.parse("tanto faz") == ("default", False)
    assert bc.parse("o padrão") == ("default", False)
    assert bc.parse("cancela") == ("cancel", False)
    assert bc.parse("que horas são") == (None, False)


def test_ask_queues_then_opens_in_chosen(monkeypatch):
    from modules import prefs

    opened = []
    monkeypatch.setattr(prefs, "get_all", lambda: {"site_browser": "ask"})
    monkeypatch.setattr(bw, "_exe", lambda k: f"C:/{k}.exe" if k in ("chrome", "edge") else None)
    real_open = bw.open_url

    def fake_open(url, browser=None, force=False):
        if force:
            opened.append((url, browser))
            return True
        return real_open(url, browser, force)

    monkeypatch.setattr(bw, "open_url", fake_open)
    bc.clear()
    assert bw.open_url("https://www.youtube.com") is False  # não abriu: guardou e vai perguntar
    assert bc.take_new() and bc.pending()
    assert bc.question() == "Em qual navegador, senhor? Chrome ou Edge?"
    reply = bc.choose("chrome")
    assert opened == [("https://www.youtube.com", "chrome")]
    assert reply == "Abrindo no Chrome, senhor." and not bc.pending()


def test_single_browser_does_not_ask(monkeypatch):
    from modules import prefs

    monkeypatch.setattr(prefs, "get_all", lambda: {"site_browser": "ask"})
    monkeypatch.setattr(bw, "_exe", lambda k: "C:/edge.exe" if k == "edge" else None)
    assert bc.should_ask() is False
