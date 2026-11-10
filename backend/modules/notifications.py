"""Central de notificações (4.2, funcionalidade 6 do backlog) — EXPERIMENTAL.

Lê as notificações do Windows (as "toasts" do canto da tela) e mostra na HUD; por voz, "quais são
minhas notificações?" resume por aplicativo.

Requisitos (opcionais, por isso fora do requirements.txt principal):
  backend\\venv\\Scripts\\python.exe -m pip install -r backend\\requirements-notificacoes.txt
e permitir o acesso em Configurações do Windows > Privacidade > Notificações. O Windows só libera
esse acesso para alguns tipos de aplicativo; se ele recusar, a aba Automação mostra o motivo e o
resto do JARVIS segue normal.

Privacidade: desligado por padrão; nada é salvo em disco (só as 30 últimas, em memória); por voz o
JARVIS diz só o aplicativo, a não ser que "ler o conteúdo" esteja ligado; com a central bloqueada
nada é mostrado nem falado; no modo foco só aparece na tela.

O Windows não oferece um jeito suportado de ligar o "Não perturbe" dele por programa, então o
"não perturbe" aqui é do JARVIS: durante o modo foco ele não fala notificações.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from collections import Counter
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger("jarvis.notifications")

MAX_ITEMS = 30
_lock = threading.Lock()
_items: list[dict[str, Any]] = []
_seen: set[int] = set()
_status: dict[str, Any] = {"available": None, "reason": "ainda não verificado"}
_reader = None  # função async que devolve a lista de notificações (trocável nos testes)


async def _winrt_reader() -> list[dict[str, Any]]:
    """Lê as notificações pelo UserNotificationListener do Windows (pacotes winrt opcionais)."""
    from winrt.windows.ui.notifications import KnownNotificationBindings, NotificationKinds
    from winrt.windows.ui.notifications.management import (
        UserNotificationListener,
        UserNotificationListenerAccessStatus,
    )

    listener = UserNotificationListener.current
    access = await listener.request_access_async()
    if access != UserNotificationListenerAccessStatus.ALLOWED:
        raise PermissionError("O Windows não liberou o acesso às notificações (Configurações > Privacidade > Notificações).")
    out = []
    for n in await listener.get_notifications_async(NotificationKinds.TOAST):
        try:
            app = n.app_info.display_info.display_name
        except Exception:  # noqa: BLE001
            app = "Aplicativo"
        texts: list[str] = []
        try:
            binding = n.notification.visual.get_binding(KnownNotificationBindings.toast_generic)
            texts = [t.text for t in binding.get_text_elements()] if binding else []
        except Exception:  # noqa: BLE001
            pass
        out.append({"id": int(n.id), "app": app, "title": texts[0] if texts else "",
                    "body": " ".join(texts[1:])[:200], "at": n.creation_time.isoformat() if n.creation_time else ""})
    return out


def _get_reader():
    global _reader
    if _reader is None:
        _reader = _winrt_reader
    return _reader


def set_reader_for_tests(fn) -> None:
    global _reader
    _reader = fn
    reset_for_tests()


async def poll() -> list[dict[str, Any]]:
    """Busca as notificações e devolve só as novas (atualiza a lista em memória e o status)."""
    try:
        current = await _get_reader()()
    except ImportError:
        _status.update(available=False, reason="Pacotes do Windows não instalados (veja backend/requirements-notificacoes.txt).")
        return []
    except PermissionError as exc:
        _status.update(available=False, reason=str(exc))
        return []
    except Exception as exc:  # noqa: BLE001
        _status.update(available=False, reason=f"O Windows recusou a leitura: {exc}")
        return []
    _status.update(available=True, reason="funcionando")
    new = []
    with _lock:
        for item in current:
            if item["id"] in _seen:
                continue
            _seen.add(item["id"])
            item = {**item, "received": datetime.now().isoformat(timespec="seconds")}
            new.append(item)
            _items.append(item)
        del _items[:-MAX_ITEMS]
        if len(_seen) > 2000:
            _seen.intersection_update({i["id"] for i in current})
    return new


def status() -> dict[str, Any]:
    return dict(_status)


def items() -> list[dict[str, Any]]:
    with _lock:
        return list(reversed(_items))


def clear() -> None:
    with _lock:
        _items.clear()


def spoken_summary(new: list[dict], read_content: bool) -> str:
    """Frase curta para as novas notificações (por padrão, só os aplicativos)."""
    if not new:
        return ""
    if len(new) == 1:
        n = new[0]
        if read_content and n.get("title"):
            return f"Notificação do {n['app']}: {n['title']}."
        return f"Nova notificação do {n['app']}, senhor."
    counts = Counter(n["app"] for n in new)
    parts = ", ".join(f"{c} do {app}" for app, c in counts.most_common(3))
    return f"{len(new)} notificações novas: {parts}."


def voice_summary(read_content: bool) -> str:
    current = items()
    if not _status.get("available"):
        return f"A central de notificações não está disponível, senhor: {_status.get('reason')}"
    if not current:
        return "Nenhuma notificação nova, senhor."
    counts = Counter(n["app"] for n in current)
    text = f"{len(current)} notificações: " + ", ".join(f"{c} do {app}" for app, c in counts.most_common(5)) + "."
    if read_content:
        latest = [n for n in current if n.get("title")][:3]
        if latest:
            text += " As mais recentes: " + "; ".join(f"{n['app']}, {n['title']}" for n in latest) + "."
    return text


async def handle_voice(norm: str) -> Optional[str]:
    from modules import prefs

    if "notificac" not in norm:
        return None
    p = await asyncio.to_thread(prefs.get_all)
    if not p.get("notifications_enabled"):
        return "A central de notificações está desligada, senhor. Ela fica em Configurações, na aba Automação."
    if any(w in norm for w in ("limpa", "limpar", "apaga", "apagar", "zera")):
        clear()
        return "Lista de notificações limpa no JARVIS, senhor. As do Windows continuam lá."
    if any(w in norm for w in ("quais", "minhas", "resume", "resumo", "tenho", "ler", "le ", "mostra")):
        return voice_summary(bool(p.get("notifications_read_content")))
    return None


def reset_for_tests() -> None:
    with _lock:
        _items.clear()
        _seen.clear()
    _status.update(available=None, reason="ainda não verificado")
