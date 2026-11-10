"""Integração Spotify Web API via OAuth 2.0, com tokens armazenados localmente."""
import json
import secrets
import time
from urllib.parse import urlencode

import requests

from config import settings

_TOKEN_PATH = settings.DATA_DIR / "spotify_token.json"
_states: set[str] = set()
_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_URL = "https://api.spotify.com/v1"
_SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"


def configured() -> bool:
    return bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET)


def connected() -> bool:
    return _TOKEN_PATH.exists()


def authorization_url() -> str:
    if not configured():
        raise RuntimeError("Spotify não configurado. Preencha SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET.")
    state = secrets.token_urlsafe(32)
    _states.add(state)
    return f"{_AUTH_URL}?{urlencode({'client_id': settings.SPOTIFY_CLIENT_ID, 'response_type': 'code', 'redirect_uri': settings.SPOTIFY_REDIRECT_URI, 'scope': _SCOPES, 'state': state})}"


def exchange_code(code: str, state: str) -> None:
    if state not in _states:
        raise ValueError("Estado OAuth do Spotify inválido ou expirado.")
    _states.discard(state)
    response = requests.post(
        _TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.SPOTIFY_REDIRECT_URI},
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
        timeout=20,
    )
    response.raise_for_status()
    token = response.json()
    token["created_at"] = time.time()
    _TOKEN_PATH.write_text(json.dumps(token, ensure_ascii=False), encoding="utf-8")


def disconnect() -> None:
    if _TOKEN_PATH.exists():
        _TOKEN_PATH.unlink()


def _access_token() -> str:
    if not _TOKEN_PATH.exists():
        raise RuntimeError("Spotify ainda não está conectado. Autorize a integração primeiro.")
    data = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
    if time.time() < data.get("created_at", 0) + data.get("expires_in", 0) - 60:
        return data["access_token"]
    if not data.get("refresh_token"):
        raise RuntimeError("Sessão do Spotify expirou. Autorize novamente.")
    response = requests.post(
        _TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": data["refresh_token"]},
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
        timeout=20,
    )
    response.raise_for_status()
    refreshed = {**data, **response.json(), "created_at": time.time()}
    _TOKEN_PATH.write_text(json.dumps(refreshed, ensure_ascii=False), encoding="utf-8")
    return refreshed["access_token"]


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token()}"}


def _request(method: str, path: str, **kwargs) -> requests.Response:
    response = requests.request(method, f"{_API_URL}{path}", headers=_headers(), timeout=20, **kwargs)
    if response.status_code == 401:
        raise RuntimeError("A autorização do Spotify expirou. Autorize novamente.")
    if response.status_code not in (200, 202, 204):
        response.raise_for_status()
    return response


def play() -> None:
    _request("PUT", "/me/player/play")


def pause() -> None:
    _request("PUT", "/me/player/pause")


def next_track() -> None:
    _request("POST", "/me/player/next")


def previous_track() -> None:
    _request("POST", "/me/player/previous")


def current_track() -> str:
    response = _request("GET", "/me/player/currently-playing")
    if response.status_code == 204:
        return "Nenhuma música está tocando no momento."
    item = response.json().get("item") or {}
    artists = ", ".join(artist.get("name", "") for artist in item.get("artists", []))
    return f"Está tocando {item.get('name', 'uma faixa desconhecida')} de {artists}."


def parse_now_playing(status_code: int, payload: dict | None) -> dict:
    """V4.2.2: faixa atual em partes para o cartão "Tocando agora". Função pura (testada)."""
    if status_code == 204 or not payload or not payload.get("item"):
        return {"state": "idle"}
    item = payload["item"]
    images = (item.get("album") or {}).get("images") or []
    # As capas vêm da maior para a menor: a de ~300 px basta para a miniatura
    image = next((img["url"] for img in images if (img.get("width") or 0) <= 320), images[-1]["url"] if images else None)
    return {
        "state": "playing" if payload.get("is_playing") else "paused",
        "title": item.get("name") or "Faixa desconhecida",
        "artist": ", ".join(a.get("name", "") for a in item.get("artists", []) if a.get("name")),
        "album": (item.get("album") or {}).get("name", ""),
        "image": image,
        "progress_ms": payload.get("progress_ms") or 0,
        "duration_ms": item.get("duration_ms") or 0,
    }


def now_playing() -> dict:
    response = _request("GET", "/me/player/currently-playing")
    return parse_now_playing(response.status_code, response.json() if response.status_code != 204 else None)


def search_and_play(query: str, playlist: bool = False) -> str:
    query = query.strip()
    if not query:
        raise ValueError("Informe o nome da música ou playlist.")
    item_type = "playlist" if playlist else "track"
    response = _request("GET", "/search", params={"q": query, "type": item_type, "limit": 1})
    items = response.json().get(f"{item_type}s", {}).get("items", [])
    if not items:
        return f"Não encontrei {item_type} com o nome '{query}'."
    item = items[0]
    if playlist:
        _request("PUT", "/me/player/play", json={"context_uri": item["uri"]})
        return f"Iniciando a playlist {item.get('name', query)}, senhor."
    _request("PUT", "/me/player/play", json={"uris": [item["uri"]]})
    artists = ", ".join(artist.get("name", "") for artist in item.get("artists", []))
    return f"Tocando {item.get('name', query)} de {artists}, senhor."


def playlist_uri(value: str) -> str:
    """Aceita 'spotify:playlist:ID' ou 'https://open.spotify.com/playlist/ID?si=...'."""
    value = (value or "").strip()
    if value.startswith("spotify:playlist:"):
        return value
    marker = "open.spotify.com/playlist/"
    if marker in value:
        pid = value.split(marker, 1)[1].split("?", 1)[0].split("/", 1)[0]
        if pid:
            return f"spotify:playlist:{pid}"
    raise ValueError("Link de playlist do Spotify inválido.")


def set_volume(percent: int) -> None:
    _request("PUT", "/me/player/volume", params={"volume_percent": max(0, min(100, int(percent)))})


def play_playlist(uri: str, ramp: bool = True, target_volume: int = 60) -> str:
    """Toca uma playlist (exige Spotify Premium e um dispositivo ativo).

    Com ramp=True o volume sobe aos poucos até target_volume. Se o dispositivo não aceitar
    controle de volume, a música toca mesmo assim.
    """
    context = playlist_uri(uri)
    if ramp:
        try:
            set_volume(10)
        except Exception:  # noqa: BLE001 - alguns dispositivos não permitem volume remoto
            ramp = False
    _request("PUT", "/me/player/play", json={"context_uri": context})
    if ramp:
        for vol in range(20, target_volume + 1, 10):
            time.sleep(0.8)
            try:
                set_volume(vol)
            except Exception:  # noqa: BLE001
                break
    return "Playlist de abertura iniciada."
