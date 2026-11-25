"""V8.11: GUARDIÃO do JARVIS — mantém o JARVIS ligado.

Roda em segundo plano (o Iniciar-JARVIS.bat liga com o pythonw, sem janela). A cada 10 s confere o backend; se ele
caiu sozinho (estava no ar e parou de responder por 45 s), liga de novo pelo Iniciar-JARVIS.bat no modo "site".

Não religa quando:
  - o JARVIS está ligando ou atualizando (o Iniciar deixa logs/iniciando.flag enquanto trabalha);
  - foi parado de propósito (o Parar-JARVIS.bat encerra o guardião antes);
  - já religou demais (no máximo 4 vezes por hora, com espera crescente: 1, 5 e 15 min entre as tentativas).
V9.5.2: também religa quando o JARVIS NUNCA respondeu desde que o guardião ligou (caiu logo ao subir, por exemplo
depois de uma atualização) e o Iniciar já terminou: antes só religava quem já tinha estado no ar.
Também deixa um "sinal de vida" (logs/guardiao.beat): com ele ativo, o ouvido offline não tenta religar junto.
Registro em logs/guardiao.log.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
PID_PATH = LOGS / "guardiao.pid"
BEAT_PATH = LOGS / "guardiao.beat"
STARTING_FLAG = LOGS / "iniciando.flag"
CHECK_EVERY_S = 10
DOWN_FOR_S = 45
STARTING_GRACE_S = 300  # o Iniciar leva até uns minutos (interface nova, dependências)
COOLDOWNS_S = (60, 300, 900)
MAX_PER_HOUR = 4
BEAT_FRESH_S = 60
NEVER_UP_S = 120  # V9.5.2: o Iniciar terminou e o JARVIS não respondeu em 2 min: religa

log = logging.getLogger("jarvis.guardiao")


class Guardian:
    """Parte pura: decide quando religar."""

    def __init__(self, started: Optional[float] = None) -> None:
        self.seen_up = False
        self.started = started if started is not None else time.time()
        self.down_since: Optional[float] = None
        self.revives: list[float] = []

    def should_revive(self, up: bool, now: float, starting_age: Optional[float]) -> bool:
        if up:
            self.seen_up, self.down_since = True, None
            return False
        if not self.seen_up:
            # V9.5.2: nunca respondeu desde que o guardião ligou. Antes esperava para sempre (quem liga é o Iniciar);
            # se o JARVIS caiu logo ao subir, ninguém religava. Agora, com o Iniciar já terminado, espera 2 min.
            if starting_age is not None and starting_age < STARTING_GRACE_S:
                return False
            if self.down_since is None:
                self.down_since = self.started  # conta desde que o guardião ligou
            if now - self.down_since < NEVER_UP_S:
                return False
        else:
            if self.down_since is None:
                self.down_since = now
            if now - self.down_since < DOWN_FOR_S:
                return False
        if starting_age is not None and starting_age < STARTING_GRACE_S:
            return False  # ligando/atualizando agora
        self.revives = [t for t in self.revives if now - t < 3600]
        if len(self.revives) >= MAX_PER_HOUR:
            return False
        if self.revives:
            wait = COOLDOWNS_S[min(len(self.revives), len(COOLDOWNS_S)) - 1]
            if now - self.revives[-1] < wait:
                return False
        self.revives.append(now)
        self.down_since = now  # dá tempo para o Iniciar trabalhar antes de contar de novo
        return True


def beat_is_fresh(now: Optional[float] = None, path: Path = BEAT_PATH) -> bool:
    """O guardião está vivo? (o ouvido offline usa para não religar junto)."""
    try:
        return (now or time.time()) - path.stat().st_mtime < BEAT_FRESH_S
    except OSError:
        return False


def _starting_age(now: float) -> Optional[float]:
    try:
        return now - STARTING_FLAG.stat().st_mtime
    except OSError:
        return None


def main() -> int:
    from ligar_jarvis import backend_up, start_hidden

    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(filename=LOGS / "guardiao.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(message)s")
    try:
        PID_PATH.write_text(str(os.getpid()), encoding="ascii")
    except OSError:
        pass
    guardian = Guardian()
    log.info("Guardião ligado.")
    while True:
        now = time.time()
        try:
            BEAT_PATH.write_text(str(int(now)), encoding="ascii")
        except OSError:
            pass
        up = backend_up()
        if guardian.should_revive(up, now, _starting_age(now)):
            log.warning("O JARVIS parou de responder há %d s; ligando de novo.", DOWN_FOR_S)
            try:
                start_hidden()
            except Exception:  # noqa: BLE001
                log.exception("Não consegui religar o JARVIS")
        time.sleep(CHECK_EVERY_S)


if __name__ == "__main__":
    if os.name != "nt":
        print("Só no Windows.")
        sys.exit(1)
    sys.exit(main())
