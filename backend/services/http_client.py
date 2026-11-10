"""Cliente HTTP único do JARVIS (refatoração 4.2).

Todas as consultas simples a serviços externos (clima, cotação, notícias) passam por aqui, com:
- uma sessão reaproveitada (conexões mantidas abertas, menos latência);
- timeout padrão em toda chamada;
- nova tentativa automática em falhas de conexão e erros 502/503/504 (somente GET);
- cache curto opcional por URL + parâmetros (`ttl` em segundos).

As funções são síncronas: nas rotas, chame com `asyncio.to_thread(...)` ou use as versões `a*`.
Erros continuam sendo os do `requests` (RequestException, HTTPError) e ValueError para JSON inválido,
então os `except` existentes no projeto seguem valendo.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (JarvisAssistant)"
_MAX_CACHE_ENTRIES = 256

_session_lock = threading.Lock()
_session: requests.Session | None = None
_cache_lock = threading.Lock()
_cache: dict[tuple, tuple[float, Any]] = {}


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=1,
        backoff_factor=0.3,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session


def session() -> requests.Session:
    """Sessão compartilhada (criada na primeira chamada)."""
    global _session
    with _session_lock:
        if _session is None:
            _session = _build_session()
        return _session


def _key(kind: str, url: str, params: dict | None, headers: dict | None) -> tuple:
    return (kind, url, tuple(sorted((params or {}).items())), tuple(sorted((headers or {}).items())))


def _cached(key: tuple) -> tuple[bool, Any]:
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.monotonic():
            return True, hit[1]
        if hit:
            _cache.pop(key, None)
    return False, None


def _store(key: tuple, value: Any, ttl: float) -> None:
    with _cache_lock:
        if len(_cache) >= _MAX_CACHE_ENTRIES:
            # descarta primeiro o que já expirou; se não bastar, o mais antigo
            now = time.monotonic()
            for k in [k for k, (exp, _) in _cache.items() if exp <= now]:
                _cache.pop(k, None)
            if len(_cache) >= _MAX_CACHE_ENTRIES:
                _cache.pop(min(_cache, key=lambda k: _cache[k][0]), None)
        _cache[key] = (time.monotonic() + ttl, value)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def request(method: str, url: str, *, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
    """Requisição crua pela sessão compartilhada (sem cache). Não chama raise_for_status."""
    return session().request(method, url, timeout=timeout, **kwargs)


def _get(kind: str, url: str, params, headers, timeout, ttl):
    key = _key(kind, url, params, headers)
    if ttl > 0:
        hit, value = _cached(key)
        if hit:
            return value
    response = session().get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    value = response.json() if kind == "json" else response.content
    if ttl > 0:
        _store(key, value, ttl)
    return value


def get_json(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    ttl: float = 0,
) -> Any:
    """GET que devolve o JSON já decodificado. Com `ttl` > 0, repete o resultado por esse tempo."""
    return _get("json", url, params, headers, timeout, ttl)


def get_bytes(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    ttl: float = 0,
) -> bytes:
    """GET que devolve o corpo em bytes (RSS, XML, imagens)."""
    return _get("bytes", url, params, headers, timeout, ttl)


async def aget_json(url: str, **kwargs) -> Any:
    return await asyncio.to_thread(get_json, url, **kwargs)


async def aget_bytes(url: str, **kwargs) -> bytes:
    return await asyncio.to_thread(get_bytes, url, **kwargs)
