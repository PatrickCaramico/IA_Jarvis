"""Gerencia as preferências persistidas do JARVIS: nome da IA, paleta de cores e widgets ativos.

Armazenado em data/jarvis_settings.json.
"""
import json
import logging
from typing import Any, Optional

from config import settings

log = logging.getLogger("jarvis.prefs")

_SETTINGS_PATH = settings.DATA_DIR / "jarvis_settings.json"

_DEFAULTS: dict[str, Any] = {
    "ai_name": "JARVIS",          # nome que o usuário dá à IA
    "color_theme": "blue",        # "blue" | "green" | "purple" | "orange" | "red"
    "background_style": "blueprint",  # V4.4: "blueprint" (planta azul) | "classic" (escuro antigo)
    "widgets": ["status", "about"],  # widgets visíveis no painel
    "widget_layout": {},             # posição e tamanho persistidos no painel
    "custom_shortcuts": {},       # atalhos personalizados: {"nome": {"apps": [...], "urls": [...]}}
    "camera_index": 0,            # índice da webcam (0 = padrão)
    "llm_provider": "openai",     # provedor usado nas próximas conversas
    "personality_mode": "direto", # direto | descontraido | formal
    "search_mode": "browser",     # "browser" | "ask" | "api"
    "default_search_mode": "browser", # modo padrão caso expire timeout (10s)
    "deep_search_allowed": False, # trava geral: pesquisa profunda com IA (Gemini+web) desativada por padrão
    "deep_search_daily_limit": 5, # limite diário máximo de pesquisas profundas
    "silent_mode": False,         # modo silencioso: silencia áudio de respostas
    "fan_mode_enabled": False,     # modo torcedor com glassmorphism do clube
    "fan_team": "palmeiras",       # time selecionado (chave de FAN_TEAMS)
    "fan_auto_on_match_day": True, # V4.4: liga sozinho em dia de jogo (agenda real ESPN + Google Notícias)
    "fan_shout_enabled": True,     # gritar frase de torcida em dia de jogo
    # --- Ativação por palmas (seções 14 e 16) ---
    "clap_wake_enabled": False,    # liga o detector de 2 palmas na página do JARVIS
    "clap_sensitivity": 5,         # 1 (menos sensível) a 10 (mais sensível)
    "clap_auto_enter": False,      # entra sozinho na central ~1,5 s após reconhecer o rosto
    "clap_scope": "always",        # "lock" (só na tela de bloqueio) | "always" (também logado)
    "clap_relock_on_fail": False,  # bloqueia a tela se a reverificação por palma falhar
    # --- Tela de bloqueio (seção 17) ---
    "lock_daily_summary": "first_login",  # "off" | "first_login" | "always"
    "lock_cards": ["clock", "weather", "spotify"],   # cartões visíveis na tela de bloqueio
    "lock_auto_relock_minutes": 0,        # 0 (desligado), 5, 10, 15 ou 30
    "lock_presence_check": False,         # checagem rápida de rosto antes de bloquear
    "lock_save_failed_photo": False,      # miniatura de rosto não reconhecido (data/intruders)
    "lock_intro_sound": "default",        # "default" | "custom" | "off"
    "lock_intro_playlist_uri": "",        # playlist do Spotify após a saudação
    "fan_intro_playlist_uri": "",         # playlist própria com o Modo Torcedor ativo
    "lock_backend_enforce": True,         # bloqueio real: rotas pessoais respondem 403 bloqueado
    "lock_guest_enabled": False,          # botão "Modo visitante" na tela de bloqueio
    # --- Modo Sentinela ---
    "sentinel_enabled": False,            # tela de bloqueio em modo sentinela (escuta palavra de ativação)
    "sentinel_wake_words": ["jarvis", "ei jarvis", "ta acordado"],
    "sentinel_show_clock": True,          # relógio e data discretos na tela bloqueada
    "sentinel_night_dim": True,           # orbe mais escuro e voz mais baixa à noite
    # --- Hidratação (seção 18) ---
    "water_vessel": "glass",              # "glass" | "bottle" | "reactor"
    "water_quick_ml": [200, 300, 500],
    "water_sound": False,
    "water_pace_hint": True,
    # --- 4.2: gatilhos condicionais e protocolos ---
    "triggers": {},                       # ajustes sobre os padrões de modules/triggers.py
    "protocols": {},                      # protocolos do usuário (modules/protocols.py)
    "screen_assist_enabled": True,        # "o que é isso na tela?" captura a tela e pergunta à IA
    "routine_suggestions_enabled": True,  # oferece ações que você repete no mesmo horário (sempre pergunta)
    "notifications_enabled": False,       # central de notificações do Windows (experimental, opcional)
    "notifications_read_content": False,  # falar o título das notificações (padrão: só o aplicativo)
    # --- V4.2.2: sons da interface ---
    "sfx_volume": 60,                     # volume geral dos sons (0 a 100)
    "sfx_mode": "all",                    # "all" | "important" (só erro e alerta) | "off"
    # --- V4.5: acessibilidade (valem também na tela de bloqueio) ---
    "a11y_text_scale": 100,               # 100 | 115 | 130 (% do tamanho do texto)
    "a11y_high_contrast": False,          # painéis mais escuros, bordas e textos mais fortes
    "a11y_reduce_motion": False,          # desliga animações (além do "reduzir movimento" do Windows)
}

A11Y_TEXT_SCALES = (100, 115, 130)

# Chaves que a tela de bloqueio pode ler sem acesso liberado (nada pessoal).
PUBLIC_KEYS = {
    "ai_name", "color_theme", "background_style", "theme_colors", "available_themes", "silent_mode",
    "fan_mode_enabled", "fan_team", "fan_team_info",
    "clap_wake_enabled", "clap_sensitivity", "clap_auto_enter", "clap_scope", "clap_relock_on_fail",
    "lock_cards", "lock_intro_sound", "lock_daily_summary", "lock_auto_relock_minutes", "lock_guest_enabled",
    "sentinel_enabled", "sentinel_wake_words", "sentinel_show_clock", "sentinel_night_dim",
    "water_vessel", "sfx_volume", "sfx_mode",
    "a11y_text_scale", "a11y_high_contrast", "a11y_reduce_motion",
}

LOCK_CARD_KEYS = ("clock", "weather", "spotify", "fan_match", "water")
WATER_VESSELS = ("glass", "bottle", "reactor")


def public_view(data: dict[str, Any]) -> dict[str, Any]:
    """Subconjunto das preferências seguro para exibir antes do acesso liberado."""
    return {k: v for k, v in data.items() if k in PUBLIC_KEYS}


def validate_patch(patch: dict[str, Any]) -> Optional[str]:
    """Valida as preferências novas (seções 14 a 18 e Sentinela). Devolve a mensagem de erro ou None."""
    bools = (
        "clap_wake_enabled", "clap_auto_enter", "clap_relock_on_fail", "lock_presence_check",
        "lock_save_failed_photo", "lock_backend_enforce", "lock_guest_enabled", "sentinel_enabled", "sentinel_show_clock",
        "sentinel_night_dim", "water_sound", "water_pace_hint", "screen_assist_enabled",
        "routine_suggestions_enabled", "notifications_enabled", "notifications_read_content",
    )
    for key in bools:
        if key in patch and not isinstance(patch[key], bool):
            return f"{key} deve ser um booleano."
    if "clap_sensitivity" in patch:
        v = patch["clap_sensitivity"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 10:
            return "clap_sensitivity deve ser um inteiro de 1 a 10."
    if "clap_scope" in patch and patch["clap_scope"] not in {"lock", "always"}:
        return "clap_scope inválido. Use 'lock' ou 'always'."
    if "lock_daily_summary" in patch and patch["lock_daily_summary"] not in {"off", "first_login", "always"}:
        return "lock_daily_summary inválido. Use 'off', 'first_login' ou 'always'."
    if "lock_cards" in patch:
        v = patch["lock_cards"]
        if not isinstance(v, list) or any(c not in LOCK_CARD_KEYS for c in v):
            return f"lock_cards inválido. Use itens de {list(LOCK_CARD_KEYS)}."
        patch["lock_cards"] = list(dict.fromkeys(v))
    if "lock_auto_relock_minutes" in patch:
        v = patch["lock_auto_relock_minutes"]
        if isinstance(v, bool) or v not in {0, 5, 10, 15, 30}:
            return "lock_auto_relock_minutes deve ser 0, 5, 10, 15 ou 30."
    if "lock_intro_sound" in patch and patch["lock_intro_sound"] not in {"default", "custom", "off"}:
        return "lock_intro_sound inválido. Use 'default', 'custom' ou 'off'."
    for key in ("lock_intro_playlist_uri", "fan_intro_playlist_uri"):
        if key in patch:
            v = patch[key]
            if not isinstance(v, str) or len(v) > 200:
                return f"{key} deve ser um texto curto."
            v = v.strip()
            if v and not (v.startswith("spotify:playlist:") or "open.spotify.com/playlist/" in v):
                return f"{key} deve ser um link ou URI de playlist do Spotify."
            patch[key] = v
    if "sentinel_wake_words" in patch:
        v = patch["sentinel_wake_words"]
        if not isinstance(v, list) or not v or any(not isinstance(w, str) or not w.strip() or len(w) > 40 for w in v):
            return "sentinel_wake_words deve ser uma lista de frases curtas."
        patch["sentinel_wake_words"] = [w.strip().lower() for w in v][:8]
    if "triggers" in patch:
        from modules import triggers

        err = triggers.validate(patch["triggers"])
        if err:
            return err
        current = _load().get("triggers") or {}
        merged = {k: {**current.get(k, {}), **v} for k, v in patch["triggers"].items()}
        patch["triggers"] = {**current, **merged}
    if "protocols" in patch:
        from modules import protocols

        err = protocols.validate(patch["protocols"])
        if err:
            return err
    if "sfx_volume" in patch:
        v = patch["sfx_volume"]
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100:
            return "sfx_volume deve ser um número de 0 a 100."
    if "sfx_mode" in patch and patch["sfx_mode"] not in {"all", "important", "off"}:
        return "sfx_mode inválido. Use 'all', 'important' ou 'off'."
    if "water_vessel" in patch and patch["water_vessel"] not in WATER_VESSELS:
        return f"water_vessel inválido. Use {list(WATER_VESSELS)}."
    if "water_quick_ml" in patch:
        v = patch["water_quick_ml"]
        if (not isinstance(v, list) or not 1 <= len(v) <= 4
                or any(isinstance(x, bool) or not isinstance(x, int) or not 20 <= x <= 3000 for x in v)):
            return "water_quick_ml deve ter de 1 a 4 valores entre 20 e 3000 ml."
    return None

# Paletas disponíveis (nome -> {primária, secundária, fundo})
THEMES = {
    "blue":   {"primary": "#22d3ee", "secondary": "#0e7490", "bg": "#05070d"},  # Branding 4.2
    "green":  {"primary": "#22c55e", "secondary": "#15803d", "bg": "#021308"},
    "purple": {"primary": "#a855f7", "secondary": "#7c3aed", "bg": "#0c0213"},
    "orange": {"primary": "#f97316", "secondary": "#c2410c", "bg": "#130801"},
    "red":    {"primary": "#ef4444", "secondary": "#b91c1c", "bg": "#130202"},
}


def _load() -> dict[str, Any]:
    if not _SETTINGS_PATH.exists():
        _save(_DEFAULTS.copy())
        return _DEFAULTS.copy()
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _DEFAULTS.copy()
        # garante que todas as chaves padrão existem
        merged = {**_DEFAULTS, **data}
        # V4.2.2: o cartão "Tocando agora" (Spotify) entra ligado uma vez em quem já tinha cartões salvos
        if not merged.get("_v422_spotify_card"):
            cards = list(merged.get("lock_cards") or [])
            if "spotify" not in cards:
                cards.append("spotify")
            merged["lock_cards"] = cards
            merged["_v422_spotify_card"] = True
            _save(merged)
        # V4.4: com a agenda real, "entrar no Modo Torcedor em dia de jogo" passa a vir ligado uma vez
        # para quem já tinha configurações salvas (dá para desligar na aba Torcedor).
        if not merged.get("_v44_fan_auto"):
            merged["fan_auto_on_match_day"] = True
            merged["_v44_fan_auto"] = True
            _save(merged)
        return merged
    except (OSError, ValueError) as exc:
        log.warning("jarvis_settings.json inválido (%s); usando padrões.", exc)
        return _DEFAULTS.copy()


def _save(data: dict[str, Any]) -> None:
    _SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all() -> dict[str, Any]:
    from modules.fan_mode import get_team_info, FAN_TEAMS
    prefs = _load()
    theme = prefs.get("color_theme", "blue")
    prefs["theme_colors"] = THEMES.get(theme, THEMES["blue"])
    prefs["available_themes"] = list(THEMES.keys())
    team_id = prefs.get("fan_team", "palmeiras")
    prefs["fan_team_info"] = get_team_info(team_id) or FAN_TEAMS["palmeiras"]
    prefs["available_fan_teams"] = list(FAN_TEAMS.keys())
    return prefs


def update(patch: Optional[dict[str, Any]] = None, **kwargs) -> dict[str, Any]:
    """Atualiza parcialmente as preferências e devolve o estado atual.
    
    Aceita um dicionário `patch` ou argumentos nomeados como `prefs.update(fan_mode_enabled=True)`.
    """
    prefs = _load()
    allowed_keys = set(_DEFAULTS.keys())
    data_to_update = dict(patch or {})
    data_to_update.update(kwargs)
    for key, value in data_to_update.items():
        if key in allowed_keys:
            prefs[key] = value
    _save(prefs)
    return get_all()


def get_ai_name() -> str:
    return _load().get("ai_name", "JARVIS")


def get_camera_index() -> int:
    return int(_load().get("camera_index", settings.CAMERA_INDEX))


def get_llm_config() -> tuple[str, str]:
    prefs = _load()
    provider = str(prefs.get("llm_provider") or settings.LLM_PROVIDER).lower()
    configured = {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
    }
    if not configured.get(provider, False):
        provider = next((name for name in ("gemini", "openai", "anthropic") if configured[name]), provider)
    mode = str(prefs.get("personality_mode") or "direto").lower()
    return provider, mode


def get_shortcuts() -> dict:
    return _load().get("custom_shortcuts", {})


def save_shortcut(name: str, apps: list[str], urls: list[str]) -> None:
    prefs = _load()
    prefs.setdefault("custom_shortcuts", {})[name] = {"apps": apps, "urls": urls}
    _save(prefs)


def delete_shortcut(name: str) -> bool:
    prefs = _load()
    shortcuts = prefs.get("custom_shortcuts", {})
    if name not in shortcuts:
        return False
    del shortcuts[name]
    prefs["custom_shortcuts"] = shortcuts
    _save(prefs)
    return True


def get_search_mode() -> str:
    mode = str(_load().get("search_mode", "ask")).lower()
    return mode if mode in {"ask", "api", "browser"} else "ask"


def get_default_search_mode() -> str:
    mode = str(_load().get("default_search_mode", "api")).lower()
    return mode if mode in {"api", "browser"} else "api"


def set_search_mode(mode: str) -> None:
    if mode in {"ask", "api", "browser"}:
        p = _load()
        p["search_mode"] = mode
        _save(p)


def is_silent_mode() -> bool:
    return bool(_load().get("silent_mode", False))


def set_silent_mode(active: bool) -> bool:
    p = _load()
    p["silent_mode"] = bool(active)
    _save(p)
    return bool(active)

