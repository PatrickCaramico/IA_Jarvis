"""V8.11: Skill Workspace (janelas e monitores). O Windows é trocado por um desktop falso."""
import asyncio
import copy

import pytest

import skills.workspace as ws
from core import confirm
from core.skills import executor, registry, router
from skills.workspace import layouts
from skills.workspace.layouts import Monitor, Window


def run(coro):
    return asyncio.run(coro)


def mons():
    return [Monitor(1, 0, 0, 1920, 1040, True), Monitor(2, 1920, 0, 3840, 1040)]


class FakeDesk:
    def __init__(self, windows, monitors=None, fg=None):
        self._windows = windows
        self._monitors = monitors or mons()
        self.fg = fg
        self.moves, self.maxed, self.mined, self.focused, self.launched = [], [], [], [], []
        self.to_launch = {}

    def monitors(self):
        return copy.deepcopy(self._monitors)

    def windows(self):
        return list(self._windows)

    def foreground(self):
        return self.fg

    def _win(self, hwnd):
        return next(w for w in self._windows if w.hwnd == hwnd)

    def move(self, hwnd, rect):
        x, y, w, h = rect
        win = self._win(hwnd)
        win.rect, win.maximized, win.minimized = (x, y, x + w, y + h), False, False
        win.monitor = next((m.index for m in self._monitors if m.left <= x < m.right), 1)
        self.moves.append((hwnd, rect))

    def maximize(self, hwnd):
        self._win(hwnd).maximized = True
        self.maxed.append(hwnd)

    def minimize(self, hwnd):
        self._win(hwnd).minimized = True
        self.mined.append(hwnd)

    def focus(self, hwnd):
        self.focused.append(hwnd)

    def launch(self, exe):
        self.launched.append(exe)
        self._windows.append(self.to_launch[exe])

    def wait_new_window(self, process, known, timeout=8.0):
        return next((w for w in self._windows if w.process.lower() == process.lower() and w.hwnd not in known), None)


def W(hwnd, process, title, monitor=1, rect=(100, 100, 900, 700), **kw):
    return Window(hwnd=hwnd, title=title, process=process, exe=kw.pop("exe", f"C:/apps/{process}"), monitor=monitor,
                  rect=rect, **kw)


@pytest.fixture
def desk(real_skills, monkeypatch):
    fake = FakeDesk([
        W(1, "chrome.exe", "YouTube - Google Chrome", 1, (0, 0, 960, 1040)),
        W(2, "Code.exe", "main.py - Visual Studio Code", 1, (960, 0, 1920, 1040)),
        W(3, "Spotify.exe", "Spotify Premium", 2, (2000, 100, 2800, 700)),
        W(4, "WINWORD.EXE", "Contrato final.docx - Word", 1, (200, 200, 1200, 900)),
    ], fg=1)
    monkeypatch.setattr(ws, "get_desktop", lambda: fake)
    return fake


# ------------------------------------------------------------------ partes puras
def test_monitors_are_numbered_primary_first():
    raw = [Monitor(0, -1920, 0, 0, 1080), Monitor(0, 0, 0, 2560, 1400, True), Monitor(0, 2560, 0, 4480, 1080)]
    assert [m.left for m in layouts.order_monitors(raw)] == [0, -1920, 2560]
    assert [m.index for m in raw if m.primary] == [1]


def test_grid_shapes_fill_the_monitor():
    m = Monitor(1, 0, 0, 1920, 1040, True)
    assert len(layouts.grid(m, 1)) == 1 and layouts.grid(m, 1)[0][2] == 1920 - 2 * layouts.GAP
    two = layouts.grid(m, 2)
    assert two[0][1] == two[1][1] and two[0][0] < two[1][0]  # metades, mesma altura
    three = layouts.grid(m, 3)
    assert three[0][3] > three[1][3] and three[1][0] == three[2][0]  # uma alta + duas empilhadas
    for x, y, w, h in layouts.grid(m, 7):
        assert 0 <= x and x + w <= 1920 and 0 <= y and y + h <= 1040


def test_fit_into_keeps_proportions_inside_the_target():
    a, b = mons()
    x, y, w, h = layouts.fit_into((480, 260, 1440, 780), a, b)
    assert b.left <= x and x + w <= b.right and (w, h) == (960, 520)


def test_find_windows_by_program_or_title():
    wins = [W(1, "chrome.exe", "YouTube"), W(2, "Code.exe", "main.py - Visual Studio Code"),
            W(3, "WINWORD.EXE", "Contrato final.docx - Word")]
    assert [w.hwnd for w in layouts.find_windows(wins, "chrome")] == [1]
    assert [w.hwnd for w in layouts.find_windows(wins, "vs code")] == [2]
    assert [w.hwnd for w in layouts.find_windows(wins, "vscode")] == [2]
    assert [w.hwnd for w in layouts.find_windows(wins, "contrato")] == [3]
    assert layouts.find_windows(wins, "photoshop") == []


def test_monitor_words():
    assert layouts.monitor_number("dois") == 2 and layouts.monitor_number("principal") == 1
    assert layouts.monitor_number("outra") == layouts.OTHER
    assert layouts.resolve_monitor(layouts.OTHER, 2, 2) == 1 and layouts.resolve_monitor(3, 1, 2) is None


# ------------------------------------------------------------------ frases
@pytest.mark.parametrize("phrase,skill_name,args", [
    ("manda o chrome pro monitor 2", "janela_para_monitor", {"app": "chrome", "monitor": 2}),
    ("jarvis leva o spotify para a outra tela", "janela_para_monitor", {"app": "spotify", "monitor": 0}),
    ("manda isso pro monitor principal", "janela_para_monitor", {"app": "", "monitor": 1}),
    ("organiza as janelas", "organizar_janelas", {"layout": "grade"}),
    ("arruma as janelas do monitor dois", "organizar_janelas", {"layout": "grade", "monitor": 2}),
    ("coloca o chrome e o vs code lado a lado", "organizar_janelas", {"layout": "lado_a_lado", "apps": ["chrome", "vs code"]}),
    ("deixa so o word na tela", "organizar_janelas", {"layout": "foco", "apps": ["word"]}),
    ("quais janelas estao abertas", "janelas_abertas", {}),
    ("salva esse layout como estudo", "salvar_workspace", {"nome": "estudo"}),
    ("abre o workspace estudo", "abrir_workspace", {"nome": "estudo"}),
    ("quais sao meus workspaces", "listar_workspaces", {}),
    ("apaga o workspace estudo", "apagar_workspace", {"nome": "estudo"}),
])
def test_phrases_reach_the_right_skill(real_skills, phrase, skill_name, args):
    sk, got = registry.match(phrase, phrase)
    assert sk.name == skill_name and got == args


@pytest.mark.parametrize("phrase", [
    "fechar aba", "abre o youtube", "abrir spotify", "modo trabalho", "modo foco", "protocolo trabalho",
    "organiza a pasta downloads", "abre a janela do navegador", "qual o clima em recife", "me avise em 10 minutos",
    "ativa o modo silencioso", "o que tenho hoje", "meu pc esta lento", "abre o layout",
])
def test_legacy_phrases_are_not_captured(real_skills, monkeypatch, phrase):
    from skills import system_guard

    monkeypatch.setattr(system_guard, "running_names", lambda: ["chrome.exe", "Spotify.exe", "explorer.exe"])
    assert registry.match(phrase, phrase) is None


# ------------------------------------------------------------------ execução
def test_move_to_other_monitor_keeps_maximized(desk):
    desk._windows[0].maximized = True
    result = run(router.try_fast_path("manda o chrome pro monitor 2"))
    assert result.ok and result.speech == "Google Chrome no monitor 2, senhor."
    hwnd, (x, y, w, h) = desk.moves[-1]
    assert hwnd == 1 and 1920 <= x and x + w <= 3840
    assert desk.maxed == [1] and desk.focused == [1]


def test_move_without_app_uses_the_front_window(desk):
    desk.fg = 2
    result = run(router.try_fast_path("manda isso pra outra tela"))
    assert result.ok and desk.moves[-1][0] == 2


def test_move_reports_single_monitor_and_unknown_app(desk):
    assert "não encontrei uma janela do photoshop" in run(executor.execute("janela_para_monitor", {"app": "photoshop", "monitor": 2})).speech.lower()
    desk._monitors = desk._monitors[:1]
    assert "só encontrei um monitor" in run(router.try_fast_path("manda o chrome pro monitor 2")).speech.lower()


def test_grid_tiles_each_monitor(desk):
    result = run(router.try_fast_path("organiza as janelas"))
    assert result.speech == "Organizei 4 janelas nos monitores, senhor."
    on_1 = [r for h, r in desk.moves if h in (1, 2, 4)]
    assert len(on_1) == 3 and all(x + w <= 1920 for x, _, w, _ in on_1)


def test_side_by_side_named_apps(desk):
    result = run(router.try_fast_path("coloca o word e o chrome lado a lado"))
    assert result.speech == "Word e Google Chrome lado a lado, senhor."
    (h1, r1), (h2, r2) = desk.moves
    assert (h1, h2) == (4, 1) and r1[0] < r2[0]


def test_focus_maximizes_and_minimizes_the_rest_of_that_monitor(desk):
    result = run(router.try_fast_path("deixa so o word na tela"))
    assert desk.maxed == [4] and sorted(desk.mined) == [1, 2]  # o Spotify (monitor 2) fica
    assert "minimizei 2 janelas" in result.speech


def test_save_and_restore_workspace(desk, tmp_path):
    assert "salvo com 4 janelas" in run(router.try_fast_path("salva esse layout como estudo")).speech
    saved = ws._load()["estudo"]["windows"]
    assert {i["process"] for i in saved} == {"chrome.exe", "Code.exe", "Spotify.exe", "WINWORD.EXE"}
    # bagunça: o Chrome foi parar no monitor 2 e o Spotify foi fechado
    desk.move(1, (2000, 50, 500, 400))
    desk._windows = [w for w in desk._windows if w.hwnd != 3]
    exe = tmp_path / "Spotify.exe"
    exe.write_text("", encoding="utf-8")
    for item in saved:
        if item["process"] == "Spotify.exe":
            item["exe"] = str(exe)
    data = ws._load()
    data["estudo"]["windows"] = saved
    ws._save(data)
    desk.to_launch[str(exe)] = W(9, "Spotify.exe", "Spotify", 1)
    desk.moves.clear()
    result = run(router.try_fast_path("abre o workspace estudo"))
    assert "4 janelas no lugar, 1 programa aberto" in result.speech
    assert desk.launched == [str(exe)]
    chrome = next(w for w in desk._windows if w.hwnd == 1)
    assert chrome.monitor == 1 and chrome.rect[2] <= 1920
    spotify = next(w for w in desk._windows if w.hwnd == 9)
    assert spotify.monitor == 2


def test_restore_unknown_workspace_lists_the_saved_ones(desk):
    run(router.try_fast_path("salva esse layout como trabalho"))
    assert "Os salvos são: trabalho" in run(router.try_fast_path("abre o workspace estudo")).speech


def test_delete_workspace_asks_first(desk):
    run(router.try_fast_path("salva esse layout como estudo"))
    result = run(router.try_fast_path("apaga o workspace estudo"))
    assert result.pending and "Apago o workspace estudo" in result.speech
    assert "estudo" in ws._load()
    assert run(confirm.answer("sim")) == "Workspace estudo apagado, senhor."
    assert "estudo" not in ws._load()


def test_list_windows_groups_by_monitor(desk):
    result = run(router.try_fast_path("quais janelas estão abertas?"))
    assert result.speech.startswith("Há 4 janelas abertas: no monitor 1, Google Chrome, VS Code e Word; no monitor 2, Spotify")
    assert result.cards[0]["type"] == "skill"


def test_outside_windows_says_so(real_skills, monkeypatch):
    monkeypatch.setattr(ws, "get_desktop", lambda: None)
    result = run(router.try_fast_path("organiza as janelas"))
    assert result.ok is False and "Windows" in result.speech
