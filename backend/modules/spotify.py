"""Integração Spotify Web API via OAuth 2.0, com tokens armazenados localmente."""
import json
import logging
import os
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
log = logging.getLogger("jarvis.spotify")
DEVICE_WAIT_S = 12  # V8.13.2: tempo para o app do Spotify aparecer depois de aberto pelo JARVIS


class SpotifyError(RuntimeError):
    """V8.13.2: falha de tocar com o motivo certo (a mensagem já é a frase para a tela)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


NO_DEVICE_MSG = "Não achei o Spotify aberto em nenhum aparelho. Abra o Spotify (no PC ou no celular) e tente de novo."
PREMIUM_MSG = "O Spotify só deixa o JARVIS escolher a música com uma conta Premium."
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


def devices() -> list[dict]:
    """V8.13.2: aparelhos com o Spotify aberto nesta conta (PC, celular, caixa de som)."""
    return list(_request("GET", "/me/player/devices").json().get("devices") or [])


def pick_device(items: list[dict]) -> dict | None:
    """O que está tocando/ativo; senão o computador; senão o primeiro. Aparelho restrito não aceita controle."""
    usable = [d for d in items if d.get("id") and not d.get("is_restricted")]
    for test in (lambda d: d.get("is_active"), lambda d: (d.get("type") or "").lower() == "computer", lambda d: True):
        found = next((d for d in usable if test(d)), None)
        if found:
            return found
    return None


def _launch_app() -> bool:
    """Abre o app do Spotify no PC (Windows), sem esperar. Devolve se conseguiu pedir."""
    if os.name != "nt":
        return False
    try:
        os.startfile("spotify:")  # type: ignore[attr-defined]  # noqa: S606 - protocolo fixo, nada vindo de fora
        return True
    except OSError:
        log.exception("Não consegui abrir o app do Spotify")
        return False


def ensure_device(launch: bool = True, wait_s: float = DEVICE_WAIT_S, sleep=time.sleep) -> str:
    """V8.13.2: id do aparelho onde tocar. Antes o JARVIS mandava tocar "em lugar nenhum" e o Spotify recusava
    (404, sem aparelho ativo) quando o app estava fechado ou parado havia um tempo. Agora escolhe um aparelho e,
    sem nenhum, abre o Spotify do PC e espera ele aparecer."""
    found = pick_device(devices())
    if found:
        return found["id"]
    if launch and _launch_app():
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            sleep(1.0)
            found = pick_device(devices())
            if found:
                return found["id"]
    raise SpotifyError("no_device", NO_DEVICE_MSG)


def _play(body: dict | None = None, launch: bool = True, device_id: str | None = None) -> None:
    """Toca no aparelho escolhido, com o motivo certo quando o Spotify recusa."""
    device_id = device_id or ensure_device(launch=launch)
    try:
        _request("PUT", "/me/player/play", params={"device_id": device_id}, json=body or None)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        if status == 403:
            raise SpotifyError("premium", PREMIUM_MSG) from exc
        if status == 404:
            raise SpotifyError("no_device", NO_DEVICE_MSG) from exc
        raise


def play() -> None:
    _play()


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


def find_track(query: str) -> dict | None:
    """V8.14.1: a primeira faixa da busca (ou None)."""
    response = _request("GET", "/search", params={"q": query.strip(), "type": "track", "limit": 1})
    items = response.json().get("tracks", {}).get("items", [])
    return items[0] if items else None


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
        _play({"context_uri": item["uri"]})  # V8.13.2: num aparelho de verdade (abre o Spotify se precisar)
        return f"Iniciando a playlist {item.get('name', query)}, senhor."
    _play({"uris": [item["uri"]]})
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


def current_volume() -> int | None:
    """V8.15.1: volume do aparelho que está com o Spotify agora (None: nenhum aparelho ou ele não informa)."""
    response = _request("GET", "/me/player")
    if response.status_code == 204:
        return None
    vol = ((response.json() or {}).get("device") or {}).get("volume_percent")
    return int(vol) if isinstance(vol, (int, float)) else None


def set_volume(percent: int, device_id: str | None = None) -> None:
    params = {"volume_percent": max(0, min(100, int(percent)))}
    if device_id:  # V8.14.1: volume de um aparelho que ainda não está tocando (antes de começar a música)
        params["device_id"] = device_id
    _request("PUT", "/me/player/volume", params=params)


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
    _play({"context_uri": context})
    if ramp:
        for vol in range(20, target_volume + 1, 10):
            time.sleep(0.8)
            try:
                set_volume(vol)
            except Exception:  # noqa: BLE001
                break
    return "Playlist de abertura iniciada."
