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
import threading
import time
import unicodedata
import urllib.error
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
# V8.11: "Jarvis, para" corta a fala/resposta na hora, mesmo com o ouvido "fechado" porque o JARVIS fala.
# Só frases inteiras desta lista (gramática fechada do Vosk): a voz do próprio JARVIS não dispara à toa.
STOP_PHRASES = (
    "jarvis para", "jarvis pare", "jarvis parar", "jarvis cancela", "jarvis cancelar", "jarvis silencio",
    "jarvis chega", "jarvis cala a boca", "jarbas para", "jarbas pare", "jarbas cancela", "jarbas chega",
)
SEND_TIMEOUT_S = 120

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


def can_barge_in(health: Optional[dict], status: Optional[dict], enabled: bool) -> bool:
    """V8.11: vale ouvir só o "Jarvis, para"? Quando o JARVIS está falando ou pensando (o ouvido normal fica
    fechado para não ouvir a própria voz), com a preferência ligada e nenhuma aba da central aberta no PC."""
    if not enabled or not health or health.get("status") not in ("ok", "online"):
        return False
    if not (health.get("speaking") or health.get("busy")):
        return False
    if status is not None and int(status.get("devices", 0)) - int(status.get("phones", 0)) > 0:
        return False
    return True


def is_stop_phrase(text: str) -> bool:
    return " ".join(_norm(w) for w in (text or "").split()) in STOP_PHRASES


def next_backoff(previous: float, ran_for: float, first: float = 2.0, cap: float = 30.0) -> float:
    """V8.11: espera antes de reabrir o microfone. Começa em 2 s e dobra até 30 s; se o ouvido tinha
    funcionado por mais de 1 min, a falha é nova e volta para 2 s (antes: sempre 30 s parado)."""
    if ran_for >= 60 or previous <= 0:
        return first
    return min(cap, previous * 2)


def match_input(wanted: str, devices: list[dict]) -> Optional[int]:
    """V6.5.8: índice do microfone escolhido no botão de áudio (nome do Windows) entre os do sounddevice.
    Prefere o MME (hostapi 0, que converte para 16 kHz sozinho); o MME corta o nome em 31 letras."""
    if not wanted:
        return None
    target = wanted.strip().lower()
    best = None
    for i, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0)) <= 0:
            continue
        name = str(dev.get("name", "")).strip().lower()
        if not name:
            continue
        if name == target or target.startswith(name) or name.startswith(target[:31]):
            if int(dev.get("hostapi", 0)) == 0:
                return i
            if best is None:
                best = i
    return best


class DeviceChanged(Exception):
    """O microfone escolhido mudou: reabre o ouvido no novo."""


# ------------------------------------------------------------------ backend
def _get(path: str) -> Optional[dict]:
    try:
        with urllib.request.urlopen(BACKEND + path, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - backend fora do ar: o ouvido só espera
        return None


def _post(path: str, payload: dict, timeout: float) -> int:
    """POST no backend. Devolve o código HTTP (0 = backend fora do ar)."""
    req = urllib.request.Request(
        BACKEND + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Jarvis-Client": "ouvido"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception as exc:  # noqa: BLE001
        log.warning("Backend não respondeu a %s: %s", path, exc)
        return 0


def send_command(text: str) -> bool:
    """Entrega o pedido (bloqueia até a resposta). Falhou ou o JARVIS estava ocupado: bipe de erro."""
    code = _post("/api/chat", {"message": text}, SEND_TIMEOUT_S)
    if 200 <= code < 300:
        return True
    log.warning("Pedido não entregue (HTTP %s): %s", code or "sem resposta", text)
    beep_error()
    return False


def cancel_current() -> bool:
    """V8.11: "Jarvis, para": corta a voz e descarta a resposta a caminho (o mesmo do botão Cancelar)."""
    return 200 <= _post("/api/cancel", {}, 5) < 300


class CommandSender:
    """V8.11: entrega os pedidos numa thread própria. Antes o envio rodava no laço do áudio e o microfone
    ficava surdo até a resposta terminar (até 120 s): o áudio acumulado era jogado fora e não dava para
    interromper. A fila é curta: pedido velho demais não serve mais."""

    def __init__(self, send=send_command) -> None:
        self._send = send
        self._queue: "queue.Queue[str]" = queue.Queue(maxsize=3)
        self._thread = threading.Thread(target=self._loop, name="ouvido-envio", daemon=True)
        self._thread.start()

    def submit(self, text: str) -> bool:
        try:
            self._queue.put_nowait(text)
            return True
        except queue.Full:
            log.warning("Fila de pedidos cheia; descartando: %s", text)
            beep_error()
            return False

    def _loop(self) -> None:
        while True:
            text = self._queue.get()
            try:
                self._send(text)
            except Exception:  # noqa: BLE001
                log.exception("Falha ao entregar o pedido")
            finally:
                self._queue.task_done()


def beep() -> None:
    try:
        import winsound

        winsound.Beep(880, 120)
    except Exception:  # noqa: BLE001
        pass


def beep_error() -> None:
    """V8.11: dois bipes graves = o pedido NÃO chegou (antes ficava só o bipe de "entendi" e silêncio)."""
    try:
        import winsound

        winsound.Beep(330, 150)
        winsound.Beep(262, 220)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ laço principal
# V6.5.19: vigia do JARVIS. Se o backend cair sozinho (o processo some sem deixar erro), o ouvido — que já
# confere o JARVIS a cada 2 s — liga de novo pelo Iniciar-JARVIS.bat. O Parar-JARVIS.bat encerra o ouvido
# antes, então parar de propósito nunca religa. No máximo uma tentativa a cada 10 minutos.
REVIVE_AFTER_S = 45
REVIVE_COOLDOWN_S = 600


def should_revive(down_since: Optional[float], now: float, last_revive: float, seen_up: bool) -> bool:
    """Religa só se o JARVIS já esteve no ar, está fora há REVIVE_AFTER_S e não tentou há pouco."""
    if not seen_up or down_since is None:
        return False
    return now - down_since >= REVIVE_AFTER_S and now - last_revive >= REVIVE_COOLDOWN_S


def revive_backend() -> None:
    import subprocess

    bat = ROOT / "Iniciar-JARVIS.bat"
    if not bat.exists():
        return
    log.warning("O JARVIS parou de responder; ligando de novo (Iniciar-JARVIS.bat site).")
    flags = 0
    if os.name == "nt":
        # console escondido (o .bat usa comandos de console) e grupo próprio: sobrevive ao Iniciar encerrar o ouvido
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    # mesmo formato do atalho jarvis://: cmd /c ""C:\caminho com espaços\Iniciar-JARVIS.bat" site"
    command = f'cmd.exe /c ""{bat}" site"'
    subprocess.Popen(command, cwd=str(ROOT), creationflags=flags, close_fds=True)  # noqa: S603


class Gate:
    """Consulta o backend a cada 2 s (não a cada quadro de áudio).

    V8.11: as consultas rodam numa thread própria (`start()`); o laço do áudio só lê o último estado.
    Antes eram até 3 pedidos HTTP de 3 s cada DENTRO do laço do áudio: com o backend lento, o microfone
    ficava até 9 s sem ser lido.
    """

    def __init__(self) -> None:
        self.at = 0.0
        self.open = False
        self.barge_in = False  # V8.11: só o "Jarvis, para" vale agora
        self.busy = False  # V8.11: o JARVIS está respondendo outro pedido
        self.device = None  # V6.5.8: microfone escolhido ("" = padrão); None = ainda não leu
        self.seen_up = False
        self.down_since: Optional[float] = None
        self.last_revive = 0.0

    def start(self) -> "Gate":
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="ouvido-estado", daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stopped.is_set():
            try:
                self.poll()
            except Exception:  # noqa: BLE001
                log.exception("Falha ao consultar o estado do JARVIS")
            self._stopped.wait(0.25)

    def stop(self) -> None:
        stopped = getattr(self, "_stopped", None)
        if stopped is not None:
            stopped.set()

    def refresh_soon(self) -> None:
        """Reconsulta já (o JARVIS vai começar a responder)."""
        self.at = 0.0

    def check(self) -> bool:
        """Último estado conhecido, sem esperar a rede (o laço do áudio nunca bloqueia aqui)."""
        return self.open

    def poll(self) -> bool:
        now = time.monotonic()
        if now - self.at >= STATE_EVERY_SECONDS:
            self.at = now
            health = _get("/api/health")
            if health:
                self.seen_up, self.down_since = True, None
            else:
                self.down_since = self.down_since or now
                if should_revive(self.down_since, now, self.last_revive, self.seen_up):
                    self.last_revive = now
                    try:
                        revive_backend()
                    except Exception as exc:  # noqa: BLE001
                        log.warning("Não consegui religar o JARVIS: %s", exc)
            status = _get("/api/lock/status") if health else None
            prefs = _get("/api/prefs") if health else None
            enabled = True
            if isinstance(prefs, dict):
                data = prefs.get("prefs", prefs)
                enabled = bool(data.get("voice_listener_enabled", True))
                self.device = str(data.get("voice_input_device") or "")
            self.open = should_listen(health, status, enabled)
            self.barge_in = (not self.open) and can_barge_in(health, status, enabled)
            self.busy = bool(health and health.get("busy"))
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

    def new_stop_recognizer():
        return KaldiRecognizer(model, SAMPLE_RATE, json.dumps(list(STOP_PHRASES) + ["[unk]"]))

    audio: "queue.Queue[bytes]" = queue.Queue(maxsize=200)
    gate = Gate()
    gate.poll()  # o primeiro estado antes de abrir o microfone (microfone escolhido)
    gate.start()
    sender = _sender()
    try:
        return _listen(test, sd, model, gate, sender, new_recognizers, new_stop_recognizer, audio)
    finally:
        gate.stop()  # a thread de estado deste microfone não sobra ao reabrir o ouvido


_SENDER: Optional[CommandSender] = None


def _sender() -> CommandSender:
    """Uma thread de envio só, mesmo quando o ouvido reabre (troca de microfone)."""
    global _SENDER
    if _SENDER is None:
        _SENDER = CommandSender()
    return _SENDER


def _listen(test, sd, model, gate, sender, new_recognizers, new_stop_recognizer, audio) -> int:  # noqa: ARG001
    wake_rec, full_rec = new_recognizers()
    stop_rec = new_stop_recognizer()
    last_stop = 0.0
    awaiting_until = 0.0  # disse só "Jarvis": a próxima frase é o pedido
    pending_wake: Optional[float] = None  # a gramática fechou a frase antes do reconhecedor completo

    def on_audio(indata, frames, t, status):  # noqa: ARG001
        try:
            audio.put_nowait(bytes(indata))
        except queue.Full:
            pass

    chosen = gate.device or ""
    index = match_input(chosen, list(sd.query_devices())) if chosen else None
    log.info("Ouvido offline ligado (modelo %s, microfone %s).", MODEL_DIR.name, chosen or "padrão do Windows")
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype="int16", channels=1, callback=on_audio,
                           device=index):
        was_open = None
        closed = False
        while True:
            chunk = audio.get()
            is_open = test or gate.check()
            if gate.device is not None and gate.device != chosen:
                raise DeviceChanged
            if is_open != was_open:
                log.info("Ouvindo." if is_open else "Em espera (central aberta, JARVIS falando ou desligado).")
                was_open = is_open
            if not is_open:
                closed = True
                awaiting_until, pending_wake = 0.0, None
                # V8.11: JARVIS falando/pensando: só a gramática do "Jarvis, para" escuta
                if gate.barge_in and stop_rec.AcceptWaveform(chunk):
                    heard_stop = json.loads(stop_rec.Result()).get("text", "")
                    if is_stop_phrase(heard_stop) and time.monotonic() - last_stop > 2.0:
                        last_stop = time.monotonic()
                        log.info("Interrupção por voz: %s", heard_stop)
                        if test:
                            print(f"PARAR: {heard_stop}")
                        else:
                            threading.Thread(target=cancel_current, name="ouvido-parar", daemon=True).start()
                            gate.refresh_soon()
                continue
            if closed:
                # descarta o que ficou pela metade enquanto estava fechado (mesma base de tempo nos dois)
                wake_rec, full_rec = new_recognizers()
                stop_rec = new_stop_recognizer()
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
            if gate.busy and is_stop_phrase(f"jarvis {command}"):  # V8.11: "Jarvis, para" com ele pensando
                threading.Thread(target=cancel_current, name="ouvido-parar", daemon=True).start()
                gate.refresh_soon()
                continue
            beep()
            sender.submit(command)  # V8.11: em outra thread; o microfone continua sendo lido
            gate.refresh_soon()  # reconsulta já (o JARVIS vai falar a resposta)


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
    wait = 0.0
    while True:
        started = time.monotonic()
        try:
            return run(args.test)
        except KeyboardInterrupt:
            return 0
        except DeviceChanged:
            log.info("Microfone trocado; reabrindo o ouvido.")
            wait = 0.0
            continue
        except Exception as exc:  # noqa: BLE001 - microfone sumiu etc.: tenta de novo (2 s, 4 s ... até 30 s)
            wait = next_backoff(wait, time.monotonic() - started)
            log.warning("Ouvido parou (%s); tentando de novo em %.0f s.", exc, wait)
            time.sleep(wait)


if __name__ == "__main__":
    sys.exit(main())
