"""Ouvido offline do JARVIS (V6.3): "Jarvis, que horas são?" com o navegador FECHADO.

Roda em segundo plano (o Iniciar-JARVIS.bat abre com pythonw.exe quando o modelo existe).
Reconhecimento 100% local com o Vosk (modelo pt-BR pequeno em %USERPROFILE%\\.jarvis-voice);
nada de áudio sai do PC e nada é gravado em disco.

Como funciona:
    1. dois reconhecedores ouvem o mesmo áudio: um só com a gramática ["jarvis", "jarbas"]
       (acorda), outro com o modelo completo e o horário de cada palavra (o pedido);
    2. quando a frase tem a palavra de ativação, o pedido é o que foi dito DEPOIS dela
       ("jarvis que horas são" -> "que horas são"); se não disse nada depois, bipa e
       ouve a próxima frase como pedido (até 8 s);
    3. o pedido vai para http://127.0.0.1:8000/api/chat e a resposta sai pela caixa do PC.

Fica quieto quando:
    - a central está aberta numa aba do PC (o reconhecimento da página já atende);
    - o JARVIS está falando (não ouve a própria voz);
    - a preferência "voice_listener_enabled" está desligada.

Uso (na pasta do projeto):
    python scripts/voice_listener.py --test      # mostra o que ouviu, não envia nada
    python scripts/voice_listener.py             # modo normal
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import queue
import re
import sys
import time
import unicodedata
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "ouvido.log"
PID_PATH = ROOT / "logs" / "ouvido.pid"
BACKEND = "http://127.0.0.1:8000"
MODEL_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".jarvis-voice" / "vosk-model-small-pt-0.3"
SAMPLE_RATE = 16000
WAKE_WORDS = ("jarvis", "jarbas")
FOLLOW_UP_SECONDS = 8.0
STATE_EVERY_SECONDS = 2.0

log = logging.getLogger("jarvis.ouvido")


# ------------------------------------------------------------------ partes puras (testadas)
def _norm(word: str) -> str:
    word = unicodedata.normalize("NFKD", word.lower())
    return "".join(c for c in word if not unicodedata.combining(c))


def wake_end(grammar_words: list[dict]) -> Optional[float]:
    """Fim (em segundos) da última palavra de ativação reconhecida pela gramática, ou None."""
    end = None
    for w in grammar_words or []:
        if _norm(str(w.get("word", ""))) in WAKE_WORDS:
            end = float(w.get("end", 0.0))
    return end


def command_after(full_words: list[dict], wake_at: float) -> str:
    """Palavras do reconhecedor completo que começam depois da ativação ("já visto que horas são"
    com a ativação até 0,6 s -> "que horas são"). Tolera 0,15 s de sobreposição."""
    words = [w for w in full_words or [] if float(w.get("start", 0.0)) >= wake_at - 0.15]
    # o fim de "jar-VIS" às vezes vira uma palavrinha logo depois da ativação ("já DIZ", "já SE")
    if words and float(words[0].get("start", 0.0)) < wake_at + 0.2 and _norm(str(words[0].get("word", ""))) in _TAIL_GHOSTS:
        words = words[1:]
    text = " ".join(str(w.get("word", "")) for w in words if w.get("word") and w.get("word") != "[unk]")
    return clean_command(text)


_TAIL_GHOSTS = {"se", "diz", "vis", "bis", "vez", "ves", "vi", "is"}


def clean_command(text: str) -> str:
    """Tira sobras da ativação no começo ("jarvis", "jarbas", "já", "visto") e espaços."""
    words = text.split()
    leftovers = set(WAKE_WORDS) | {"ja", "visto", "vis", "jar", "bas"}
    while words and _norm(words[0]) in leftovers:
        words.pop(0)
    return re.sub(r"\s+", " ", " ".join(words)).strip()


def should_listen(health: Optional[dict], status: Optional[dict], enabled: bool) -> bool:
    """O ouvido só atende com o backend no ar, a preferência ligada, o JARVIS calado
    e NENHUMA aba da central aberta no PC (celulares não contam)."""
    if not enabled or not health or health.get("status") not in ("ok", "online"):
        return False
    if health.get("speaking"):
        return False
    if status is not None:
        pc_tabs = int(status.get("devices", 0)) - int(status.get("phones", 0))
        if pc_tabs > 0:
            return False
    return True


# ------------------------------------------------------------------ backend
def _get(path: str) -> Optional[dict]:
    try:
        with urllib.request.urlopen(BACKEND + path, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - backend fora do ar: o ouvido só espera
        return None


def send_command(text: str) -> None:
    body = json.dumps({"message": text}).encode("utf-8")
    req = urllib.request.Request(
        BACKEND + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json", "X-Jarvis-Client": "ouvido"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("Pedido não entregue: %s", exc)


def beep() -> None:
    try:
        import winsound

        winsound.Beep(880, 120)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ laço principal
class Gate:
    """Consulta o backend a cada 2 s (não a cada quadro de áudio)."""

    def __init__(self) -> None:
        self.at = 0.0
        self.open = False

    def check(self) -> bool:
        now = time.monotonic()
        if now - self.at >= STATE_EVERY_SECONDS:
            self.at = now
            health = _get("/api/health")
            status = _get("/api/lock/status") if health else None
            prefs = _get("/api/prefs") if health else None
            enabled = True
            if isinstance(prefs, dict):
                data = prefs.get("prefs", prefs)
                enabled = bool(data.get("voice_listener_enabled", True))
            self.open = should_listen(health, status, enabled)
        return self.open


def run(test: bool) -> int:
    try:
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model, SetLogLevel
    except ImportError:
        log.error("Faltam pacotes: pip install -r scripts/requirements-ouvido.txt")
        return 2
    if not MODEL_DIR.exists():
        log.error("Modelo não encontrado em %s", MODEL_DIR)
        return 2

    SetLogLevel(-1)
    model = Model(str(MODEL_DIR))

    def new_recognizers():
        wake = KaldiRecognizer(model, SAMPLE_RATE, json.dumps(list(WAKE_WORDS) + ["[unk]"]))
        wake.SetWords(True)
        full = KaldiRecognizer(model, SAMPLE_RATE)
        full.SetWords(True)
        return wake, full

    wake_rec, full_rec = new_recognizers()
    audio: "queue.Queue[bytes]" = queue.Queue(maxsize=200)
    gate = Gate()
    awaiting_until = 0.0  # disse só "Jarvis": a próxima frase é o pedido
    pending_wake: Optional[float] = None  # a gramática fechou a frase antes do reconhecedor completo

    def on_audio(indata, frames, t, status):  # noqa: ARG001
        try:
            audio.put_nowait(bytes(indata))
        except queue.Full:
            pass

    log.info("Ouvido offline ligado (modelo %s).", MODEL_DIR.name)
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype="int16", channels=1, callback=on_audio):
        was_open = None
        closed = False
        while True:
            chunk = audio.get()
            is_open = test or gate.check()
            if is_open != was_open:
                log.info("Ouvindo." if is_open else "Em espera (central aberta, JARVIS falando ou desligado).")
                was_open = is_open
            if not is_open:
                closed = True
                awaiting_until, pending_wake = 0.0, None
                continue
            if closed:
                # descarta o que ficou pela metade enquanto estava fechado (mesma base de tempo nos dois)
                wake_rec, full_rec = new_recognizers()
                closed = False
            # os dois recebem o mesmo áudio desde a criação: os horários das palavras são comparáveis
            if wake_rec.AcceptWaveform(chunk):
                at = wake_end(json.loads(wake_rec.Result()).get("result", []))
                if at is not None:
                    pending_wake = at
            if not full_rec.AcceptWaveform(chunk):
                continue
            full = json.loads(full_rec.Result())
            at = pending_wake
            if at is None:
                at = wake_end(json.loads(wake_rec.FinalResult()).get("result", []))
            pending_wake = None
            full_words = full.get("result", [])
            heard = full.get("text", "")
            if not heard:
                continue
            if at is not None:
                command = command_after(full_words, at)
            elif time.monotonic() < awaiting_until:
                command = clean_command(heard)
            else:
                if test:
                    print(f"(ignorado) {heard}")
                continue
            if not command:
                beep()
                awaiting_until = time.monotonic() + FOLLOW_UP_SECONDS
                log.info("Ativação ouvida; aguardando o pedido.")
                continue
            awaiting_until = 0.0
            log.info("Pedido: %s", command)
            if test:
                print(f"PEDIDO: {command}")
                continue
            beep()
            send_command(command)
            gate.at = 0.0  # reconsulta já (o JARVIS vai falar a resposta)


def setup_logging(to_console: bool) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding="utf-8")]
    if to_console:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ouvido offline do JARVIS")
    parser.add_argument("--test", action="store_true", help="mostra o que ouviu, não envia nada")
    args = parser.parse_args()
    setup_logging(to_console=args.test)
    if not args.test:
        try:  # o Parar-JARVIS.bat e o Iniciar (que troca o antigo) encerram por este número
            PID_PATH.write_text(str(os.getpid()), encoding="ascii")
        except OSError:
            pass
    while True:
        try:
            return run(args.test)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:  # noqa: BLE001 - microfone sumiu etc.: tenta de novo em 30 s
            log.warning("Ouvido parou (%s); tentando de novo em 30 s.", exc)
            time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())
