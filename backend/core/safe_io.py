"""V8.3.2: gravar arquivos numa pasta do OneDrive sem "Acesso negado".

O JARVIS grava num arquivo temporário e troca pelo definitivo (assim um arquivo nunca fica pela metade). No
OneDrive, enquanto ele sincroniza o arquivo definitivo, essa troca às vezes falha com "[WinError 5] Acesso
negado" (no log: o cache de partidas, fan_cache.json). Aqui a troca tenta de novo por um instante e, se o
arquivo continuar preso, grava o conteúdo direto nele (o OneDrive deixa escrever, só não deixa trocar).
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

TRIES = 6
DELAY_S = 0.15


def replace_file(tmp: Path | str, target: Path | str, tries: int = TRIES, delay: float = DELAY_S, sleep=time.sleep) -> None:
    """Troca `target` por `tmp`. Resiste ao arquivo preso pelo OneDrive/antivírus por alguns instantes."""
    tmp, target = Path(tmp), Path(target)
    last: OSError | None = None
    for attempt in range(tries):
        try:
            os.replace(tmp, target)
            return
        except PermissionError as exc:  # WinError 5 / 32: preso por outro programa
            last = exc
            if attempt < tries - 1:
                sleep(delay * (attempt + 1))
    try:  # último recurso: copia o conteúdo por cima (o arquivo continua o mesmo, só muda o que tem dentro)
        shutil.copyfile(tmp, target)
        tmp.unlink(missing_ok=True)
    except OSError as exc:
        raise (last or exc) from exc


def write_text(target: Path | str, text: str, encoding: str = "utf-8") -> None:
    """Grava um texto inteiro com segurança (temporário + troca resistente)."""
    target = Path(target)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    replace_file(tmp, target)
