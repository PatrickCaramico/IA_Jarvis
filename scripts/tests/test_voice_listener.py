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
    ok = {"status": "ok", "speaking": False}  # o que /api/health devolve de verdade
    assert vl.should_listen(ok, {"devices": 0, "phones": 0}, True)
    assert vl.should_listen(ok, {"devices": 1, "phones": 1}, True)  # só o celular: ouve
    assert not vl.should_listen(ok, {"devices": 2, "phones": 1}, True)  # aba no PC: a página atende
    assert not vl.should_listen({"status": "online", "speaking": True}, None, True)
    assert not vl.should_listen(ok, None, False)
    assert not vl.should_listen(None, None, True)


def test_match_input_prefers_mme_and_truncated_names():
    devs = [
        {"name": "Mapeador de som da Microsoft - Input", "hostapi": 0, "max_input_channels": 2},
        {"name": "Microfone (USB PnP Audio Device", "hostapi": 0, "max_input_channels": 1},
        {"name": "Alto-falantes (USB PnP Audio Device)", "hostapi": 0, "max_input_channels": 0},
        {"name": "Microfone (USB PnP Audio Device)", "hostapi": 1, "max_input_channels": 1},
    ]
    assert vl.match_input("Microfone (USB PnP Audio Device)", devs) == 1
    assert vl.match_input("", devs) is None
    assert vl.match_input("Headset que não existe", devs) is None


def test_watchdog_revives_only_after_real_outage():
    assert not vl.should_revive(None, 100, 0, True)              # no ar
    assert not vl.should_revive(80, 100, 0, False)               # nunca esteve no ar (ainda subindo)
    assert not vl.should_revive(80, 100, 0, True)                # fora há só 20 s
    assert vl.should_revive(50, 100, -1000, True)                # fora há 50 s: religa
    assert not vl.should_revive(50, 100, 0, True)                # tentou há pouco: espera


# ------------------------------------------------------------------ V8.11
def test_barge_in_only_while_jarvis_talks_or_thinks():
    ok = {"status": "ok"}
    assert not vl.can_barge_in({**ok, "speaking": False, "busy": False}, None, True)
    assert vl.can_barge_in({**ok, "speaking": True}, None, True)
    assert vl.can_barge_in({**ok, "busy": True}, {"devices": 1, "phones": 1}, True)
    assert not vl.can_barge_in({**ok, "speaking": True}, None, False)  # ouvido desligado
    assert not vl.can_barge_in({**ok, "speaking": True}, {"devices": 2, "phones": 1}, True)  # central aberta no PC
    assert not vl.can_barge_in(None, None, True)


def test_stop_phrases_are_exact():
    assert vl.is_stop_phrase("jarvis para")
    assert vl.is_stop_phrase("Jarvis  silêncio")
    assert not vl.is_stop_phrase("jarvis para onde vamos")
    assert not vl.is_stop_phrase("para")


def test_backoff_grows_and_resets_after_a_good_run():
    assert vl.next_backoff(0, 0) == 2.0
    assert vl.next_backoff(2.0, 1) == 4.0
    assert vl.next_backoff(16.0, 1) == 30.0
    assert vl.next_backoff(30.0, 1) == 30.0
    assert vl.next_backoff(30.0, 120) == 2.0  # funcionou 2 min: falha nova começa do início


def test_sender_does_not_block_the_audio_loop():
    import threading

    release, sent = threading.Event(), []

    def slow_send(text):
        release.wait(5)
        sent.append(text)

    sender = vl.CommandSender(send=slow_send)
    assert sender.submit("que horas são")  # volta na hora, mesmo com o envio preso
    assert sender.submit("e amanhã?")
    release.set()
    sender._queue.join()
    assert sent == ["que horas são", "e amanhã?"]


def test_send_command_beeps_on_busy(monkeypatch):
    beeps = []
    monkeypatch.setattr(vl, "_post", lambda path, payload, timeout: 409)
    monkeypatch.setattr(vl, "beep_error", lambda: beeps.append(1))
    assert vl.send_command("oi") is False
    assert beeps == [1]


def test_gate_check_never_touches_the_network(monkeypatch):
    calls = []
    monkeypatch.setattr(vl, "_get", lambda path: calls.append(path))
    gate = vl.Gate()
    gate.open = True
    assert gate.check() is True
    assert calls == []
