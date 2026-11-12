"""V6.5.8: sites abrem numa janela média no canto da tela."""
from modules import browser_window as bw


def test_compact_rect_bottom_right():
    x, y, w, h = bw.compact_rect((0, 0, 1920, 1040))
    assert (w, h) == (1152, 624)
    assert x + w == 1920 - 24 and y + h == 1040 - 24


def test_compact_rect_small_screen_stays_inside():
    x, y, w, h = bw.compact_rect((0, 0, 800, 600))
    assert x >= 0 and y >= 0 and x + w <= 800 and y + h <= 600


def test_tab_mode_uses_old_behaviour(monkeypatch):
    from modules import prefs

    opened = []
    monkeypatch.setattr(prefs, "get_all", lambda: {"site_window_mode": "tab"})
    monkeypatch.setattr(bw.webbrowser, "open", lambda url, new=0, autoraise=True: opened.append(url))
    assert bw.open_url("https://www.youtube.com") is False
    assert opened == ["https://www.youtube.com"]
