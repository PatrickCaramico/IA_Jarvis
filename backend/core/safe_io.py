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


# ------------------------------------------------------------------ V8.11: JSON com cache e escrita atômica
# Antes, prefs/memória/eventos liam o arquivo do disco a CADA chamada (várias por pedido, no laço principal) e
# gravavam por cima direto: uma queda de energia no meio deixava o JSON pela metade, a leitura devolvia os
# padrões e a próxima gravação apagava as configurações sem aviso.
import copy  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import threading  # noqa: E402
from datetime import datetime  # noqa: E402

_log = logging.getLogger("jarvis.safe_io")
_json_cache: dict[str, tuple[tuple[int, int], object]] = {}
_json_lock = threading.Lock()
_saved_corrupt: set[tuple[str, int, int]] = set()


def _stat_key(path: Path) -> tuple[int, int]:
    st = path.stat()
    return (st.st_mtime_ns, st.st_size)


def _keep_corrupt_copy(path: Path, key: tuple[int, int]) -> None:
    """Guarda o arquivo estragado ao lado (uma vez) antes que uma gravação nova o substitua."""
    marker = (str(path), *key)
    if marker in _saved_corrupt:
        return
    _saved_corrupt.add(marker)
    dest = path.with_name(f"{path.stem}.corrompido-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
    try:
        shutil.copyfile(path, dest)
        _log.error("Arquivo %s estava inválido; cópia guardada em %s.", path.name, dest.name)
    except OSError:
        _log.exception("Não consegui guardar a cópia do arquivo inválido %s", path)


def read_json(path: Path | str) -> object:
    """Lê um JSON, reaproveitando a leitura anterior enquanto o arquivo não mudar (data e tamanho).

    Devolve sempre uma CÓPIA (quem chama pode alterar à vontade). Arquivo ausente: FileNotFoundError.
    JSON inválido: guarda uma cópia do arquivo estragado e devolve a última versão boa lida nesta execução;
    se não houver nenhuma, levanta ValueError (quem chama já cai nos padrões).
    """
    path = Path(path)
    name = str(path)
    key = _stat_key(path)
    with _json_lock:
        hit = _json_cache.get(name)
        if hit and hit[0] == key:
            return copy.deepcopy(hit[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        _keep_corrupt_copy(path, key)
        with _json_lock:
            hit = _json_cache.get(name)
        if hit is not None:
            _log.warning("Usando a última versão boa de %s (o arquivo no disco está inválido).", path.name)
            return copy.deepcopy(hit[1])
        raise
    with _json_lock:
        _json_cache[name] = (key, copy.deepcopy(data))
    return data


def write_json(path: Path | str, data: object, indent: int | None = 2) -> None:
    """Grava o JSON de forma atômica (temporário + troca) e atualiza o cache de leitura."""
    path = Path(path)
    write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))
    try:
        key = _stat_key(path)
    except OSError:
        return
    with _json_lock:
        _json_cache[str(path)] = (key, copy.deepcopy(data))


def forget_json_cache() -> None:
    """Para os testes: esquece todas as leituras guardadas."""
    with _json_lock:
        _json_cache.clear()
