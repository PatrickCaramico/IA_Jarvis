"""Integração Google Calendar via OAuth 2.0, com tokens armazenados somente localmente."""
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

from config import settings

_TOKEN_PATH = settings.DATA_DIR / "google_calendar_token.json"
_states: set[str] = set()
_SCOPES = "https://www.googleapis.com/auth/calendar.readonly"
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def connected() -> bool:
    return _TOKEN_PATH.exists()


def authorization_url() -> str:
    if not configured():
        raise RuntimeError("Google Calendar não configurado. Preencha GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET.")
    state = secrets.token_urlsafe(32)
    _states.add(state)
    query = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return f"{_AUTH_URL}?{query}"


def exchange_code(code: str, state: str) -> None:
    if state not in _states:
        raise ValueError("Estado OAuth inválido ou expirado.")
    _states.discard(state)
    response = requests.post(_TOKEN_URL, data={
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=20)
    response.raise_for_status()
    token = response.json()
    token["created_at"] = time.time()
    _TOKEN_PATH.write_text(json.dumps(token, ensure_ascii=False), encoding="utf-8")


def disconnect() -> None:
    if _TOKEN_PATH.exists():
        _TOKEN_PATH.unlink()


def _token_data() -> dict:
    if not _TOKEN_PATH.exists():
        raise RuntimeError("Google Calendar ainda não está conectado.")
    return json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))


def _access_token() -> str:
    data = _token_data()
    expires_at = data.get("created_at", 0) + data.get("expires_in", 0)
    if data.get("access_token") and datetime.now().timestamp() < expires_at - 60:
        return data["access_token"]
    if not data.get("refresh_token"):
        raise RuntimeError("Sessão do Google expirou. Conecte o calendário novamente.")
    response = requests.post(_TOKEN_URL, data={
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": data["refresh_token"],
        "grant_type": "refresh_token",
    }, timeout=20)
    response.raise_for_status()
    refreshed = {**data, **response.json(), "created_at": datetime.now().timestamp()}
    _TOKEN_PATH.write_text(json.dumps(refreshed, ensure_ascii=False), encoding="utf-8")
    return refreshed["access_token"]


def upcoming_events(days: int = 14, limit: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    response = requests.get(_EVENTS_URL, headers={"Authorization": f"Bearer {_access_token()}"}, params={
        "timeMin": now.isoformat(),
        "timeMax": (now + timedelta(days=days)).isoformat(),
        "maxResults": limit,
        "singleEvents": "true",
        "orderBy": "startTime",
    }, timeout=20)
    if response.status_code == 401:
        raise RuntimeError("A autorização do Google expirou. Conecte o calendário novamente.")
    response.raise_for_status()
    events = []
    for item in response.json().get("items", []):
        start = item.get("start", {})
        events.append({
            "id": item.get("id"),
            "title": item.get("summary", "Sem título"),
            "start": start.get("dateTime") or start.get("date"),
            "location": item.get("location", ""),
            "link": item.get("htmlLink", ""),
        })
    return events
