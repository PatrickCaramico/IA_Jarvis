"""Partes puras do ouvido offline (V6.3): ativação, recorte do pedido e quando escutar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import voice_listener as vl  # noqa: E402


def w(word, start, end):
    return {"word": word, "start": start, "end": end}


def test_wake_end_finds_jarbas():
    assert vl.wake_end([w("jarbas", 0.1, 0.6)]) == 0.6
    assert vl.wake_end([w("[unk]", 0.1, 0.6)]) is None
    assert vl.wake_end([]) is None


def test_command_after_cuts_wake_word_garbage():
    # o modelo completo ouve "jarvis" como "já visto"
    full = [w("já", 0.1, 0.3), w("visto", 0.3, 0.6), w("que", 0.7, 0.8), w("horas", 0.8, 1.0), w("são", 1.0, 1.2)]
    assert vl.command_after(full, 0.6) == "que horas são"


def test_command_after_strips_leftovers_in_overlap():
    # gravação real: "Jarvis, coloca leite na lista" -> o modelo completo ouviu "já se colocar leite"
    full = [w("já", 0.15, 0.39), w("se", 0.66, 0.84), w("colocar", 1.02, 1.56), w("leite", 1.56, 1.89)]
    assert vl.command_after(full, 0.525) == "colocar leite"
    full = [w("já", 0.15, 0.42), w("diz", 0.45, 0.75), w("que", 0.75, 0.9), w("horas", 0.9, 1.2)]
    assert vl.command_after(full, 0.48) == "que horas"
    # "se" bem depois da ativação é parte do pedido
    full = [w("já", 0.1, 0.3), w("se", 1.5, 1.6), w("chover", 1.6, 2.0)]
    assert vl.command_after(full, 0.4) == "se chover"
    assert vl.clean_command("jarvis que horas são") == "que horas são"
    assert vl.clean_command("já visto") == ""


def test_should_listen_gates():
    ok = {"status": "online", "speaking": False}
    assert vl.should_listen(ok, {"devices": 0, "phones": 0}, True)
    assert vl.should_listen(ok, {"devices": 1, "phones": 1}, True)  # só o celular: ouve
    assert not vl.should_listen(ok, {"devices": 2, "phones": 1}, True)  # aba no PC: a página atende
    assert not vl.should_listen({"status": "online", "speaking": True}, None, True)
    assert not vl.should_listen(ok, None, False)
    assert not vl.should_listen(None, None, True)
