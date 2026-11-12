"""Rotas de perfil, 'sobre mim' e preferências."""

import logging
import asyncio
import base64
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from modules import about, face, prefs, deep_search_quota, fan_mode, sports_provider
from modules import access, lock_pin
from services.llm_orchestrator import get_quota_cooldown
from fastapi import APIRouter
from core import speech

log = logging.getLogger("jarvis.profile")
router = APIRouter()


class ProfileRequest(BaseModel):
    name: str = ""
    photo: str  # data URL (data:image/jpeg;base64,...) ou Base64 puro


class AboutRequest(BaseModel):
    text: str = ""


@router.get("/api/about")
async def get_about() -> dict:
    return {"text": about.get_about()}


@router.post("/api/about")
async def save_about(req: AboutRequest) -> dict:
    return {"status": "ok", "text": about.save_about(req.text)}


@router.get("/api/profile")
async def get_profile() -> dict:
    # Antes do acesso liberado, o nome não é revelado (seção 17.0).
    restricted = access.is_restricted()
    return {
        "has_photo": face.has_profile(),
        "name": "" if restricted else face.get_name(),
        "access": access.snapshot(),
    }


@router.get("/api/profile/photo")
async def get_profile_photo() -> FileResponse:
    if not face.has_profile():
        raise HTTPException(status_code=404, detail="Sem foto de perfil.")
    return FileResponse(face.PHOTO_PATH, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/api/profile")
async def save_profile(req: ProfileRequest) -> dict:
    try:
        image_bytes = base64.b64decode(req.photo.split(",", 1)[-1])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Foto inválida.") from exc
    if face.has_profile() and access.is_restricted() and lock_pin.has_pin():
        raise HTTPException(
            status_code=403,
            detail="Para trocar a foto facial, entre primeiro com o rosto ou o PIN.",
        )
    try:
        await asyncio.to_thread(face.save_profile, image_bytes, req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Falha ao salvar perfil")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "name": face.get_name()}


# ---------------------------------------------------------------- preferências (Fase 1 e ajustes)
class PrefsRequest(BaseModel):
    voice_style: str | None = None  # V6.1
    briefing_news_themes: list[dict] | None = None  # V6.2
    voice_listener_enabled: bool | None = None  # V6.3: ouvido offline
    news_notify_enabled: bool | None = None  # V6.5: notícias no celular
    site_browser: str | None = None  # V6.5.11: navegador dos sites ("ask", "default", "chrome"...)
    ai_name: str | None = None
    color_theme: str | None = None
    background_style: str | None = None
    widgets: list[str] | None = None
    camera_index: int | None = None
    llm_provider: str | None = None
    personality_mode: str | None = None
    search_mode: str | None = None
    default_search_mode: str | None = None
    deep_search_allowed: bool | None = None
    deep_search_daily_limit: int | None = None
    silent_mode: bool | None = None
    fan_mode_enabled: bool | None = None
    fan_team: str | None = None
    fan_auto_on_match_day: bool | None = None
    fan_shout_enabled: bool | None = None
    widget_layout: dict | None = None
    # Palmas (seções 14 e 16)
    clap_wake_enabled: bool | None = None
    clap_sensitivity: int | None = None
    clap_auto_enter: bool | None = None
    clap_scope: str | None = None
    clap_relock_on_fail: bool | None = None
    # Tela de bloqueio (seção 17)
    lock_daily_summary: str | None = None
    lock_cards: list[str] | None = None
    lock_auto_relock_minutes: int | None = None
    lock_presence_check: bool | None = None
    lock_save_failed_photo: bool | None = None
    lock_intro_sound: str | None = None
    lock_intro_playlist_uri: str | None = None
    fan_intro_playlist_uri: str | None = None
    lock_backend_enforce: bool | None = None
    lock_guest_enabled: bool | None = None
    # Modo Sentinela
    sentinel_enabled: bool | None = None
    hands_free_enabled: bool | None = None  # "Jarvis, ..." com a central aberta
    follow_up_enabled: bool | None = None   # conversa contínua
    sentinel_wake_words: list[str] | None = None
    sentinel_show_clock: bool | None = None
    sentinel_night_dim: bool | None = None
    # Hidratação (seção 18)
    water_vessel: str | None = None
    water_quick_ml: list[int] | None = None
    water_sound: bool | None = None
    water_pace_hint: bool | None = None
    # 4.2: gatilhos condicionais e protocolos
    triggers: dict | None = None
    protocols: dict | None = None
    screen_assist_enabled: bool | None = None
    routine_suggestions_enabled: bool | None = None
    notifications_enabled: bool | None = None
    notifications_read_content: bool | None = None
    # V4.2.2: sons
    sfx_volume: int | None = None
    sfx_mode: str | None = None
    # V4.5: acessibilidade
    a11y_text_scale: int | None = None
    a11y_high_contrast: bool | None = None
    a11y_reduce_motion: bool | None = None


@router.get("/api/prefs")
async def get_prefs() -> dict:
    """Retorna todas as preferências do JARVIS (nome da IA, tema de cores, widgets, câmera, cota, cooldown).

    Com a central bloqueada ou no modo visitante, devolve só as chaves públicas.
    """
    data = prefs.get_all()
    if access.is_restricted():
        return {
            **prefs.public_view(data),
            "restricted": True,
            "access": access.snapshot(),
        }
    data["camera_index"] = prefs.get_camera_index()
    data["deep_search_quota"] = deep_search_quota.get_status()
    in_cooldown, remaining = get_quota_cooldown()
    data["ai_cooldown"] = {"active": in_cooldown, "remaining": remaining}
    return data


@router.patch("/api/prefs")
async def update_prefs(req: PrefsRequest) -> dict:
    """Atualiza parcialmente as preferências."""
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    if "color_theme" in patch and patch["color_theme"] not in prefs.THEMES:
        raise HTTPException(
            status_code=400,
            detail=f"Tema desconhecido. Use: {list(prefs.THEMES.keys())}",
        )
    if "a11y_text_scale" in patch and patch["a11y_text_scale"] not in prefs.A11Y_TEXT_SCALES:
        raise HTTPException(status_code=400, detail="a11y_text_scale inválido. Use 100, 115 ou 130.")
    if "briefing_news_themes" in patch:
        from modules.briefing import validate_news_themes

        err = validate_news_themes(patch["briefing_news_themes"])
        if err:
            raise HTTPException(status_code=400, detail=err)
    if "voice_style" in patch:
        from modules.tts import VOICE_STYLES

        if patch["voice_style"] not in VOICE_STYLES:
            raise HTTPException(status_code=400, detail="Estilo de voz inválido.")
    if "site_browser" in patch:  # V6.5.11
        from modules.browser_choice import NAMES

        if patch["site_browser"] not in {"ask", "default", *NAMES}:
            raise HTTPException(status_code=400, detail="Navegador inválido.")
    if "background_style" in patch and patch["background_style"] not in {"blueprint", "classic", "space"}:
        raise HTTPException(status_code=400, detail="background_style inválido. Use 'blueprint', 'space' ou 'classic'.")
    if "llm_provider" in patch and patch["llm_provider"] not in {
        "openai",
        "gemini",
        "anthropic",
    }:
        raise HTTPException(
            status_code=400,
            detail="Provedor inválido. Use openai, gemini ou anthropic.",
        )
    if "personality_mode" in patch and patch["personality_mode"] not in {
        "direto",
        "descontraido",
        "formal",
    }:
        raise HTTPException(status_code=400, detail="Modo de personalidade inválido.")
    if "search_mode" in patch and patch["search_mode"] not in prefs.SEARCH_MODES:
        raise HTTPException(
            status_code=400,
            detail="search_mode inválido. Use 'auto', 'ask', 'api' ou 'browser'.",
        )
    if "default_search_mode" in patch and patch["default_search_mode"] not in {
        "api",
        "browser",
    }:
        raise HTTPException(
            status_code=400,
            detail="default_search_mode inválido. Use 'api' ou 'browser'.",
        )
    if "deep_search_allowed" in patch and not isinstance(patch["deep_search_allowed"], bool):
        raise HTTPException(status_code=400, detail="deep_search_allowed deve ser um booleano.")
    if "deep_search_daily_limit" in patch and (
        not isinstance(patch["deep_search_daily_limit"], int) or patch["deep_search_daily_limit"] < 0
    ):
        raise HTTPException(
            status_code=400,
            detail="deep_search_daily_limit deve ser um número inteiro maior ou igual a zero.",
        )
    if "silent_mode" in patch and not isinstance(patch["silent_mode"], bool):
        raise HTTPException(status_code=400, detail="silent_mode deve ser um booleano.")
    if "fan_mode_enabled" in patch and not isinstance(patch["fan_mode_enabled"], bool):
        raise HTTPException(status_code=400, detail="fan_mode_enabled deve ser um booleano.")
    if "fan_team" in patch and patch["fan_team"] not in fan_mode.FAN_TEAMS:
        raise HTTPException(
            status_code=400,
            detail=f"Time inválido. Use: {list(fan_mode.FAN_TEAMS.keys())}",
        )
    if "fan_auto_on_match_day" in patch and not isinstance(patch["fan_auto_on_match_day"], bool):
        raise HTTPException(status_code=400, detail="fan_auto_on_match_day deve ser um booleano.")
    if "fan_shout_enabled" in patch and not isinstance(patch["fan_shout_enabled"], bool):
        raise HTTPException(status_code=400, detail="fan_shout_enabled deve ser um booleano.")
    error = prefs.validate_patch(patch)
    if error:
        raise HTTPException(status_code=400, detail=error)
    previous = prefs.get_all()
    updated = prefs.update(patch)
    if "fan_mode_enabled" in patch and bool(patch["fan_mode_enabled"]) != bool(previous.get("fan_mode_enabled")):
        sports_provider.record_manual_activation(
            bool(patch["fan_mode_enabled"]), updated.get("fan_team", "palmeiras")
        )
    if "lock_backend_enforce" in patch:
        await speech.broadcast_access()
    return updated


# ---------------------------------------------------------------- V4.2.2: exportar e importar ajustes
# Só preferências (aparência, palmas, bloqueio, sons...). Não vão: chaves de API, PIN, rosto,
# memórias, "Sobre mim" e o índice da câmera (muda de um computador para outro).
EXPORT_EXCLUDE = {"camera_index"}


@router.get("/api/prefs/export")
async def export_prefs() -> dict:
    """Baixa as preferências em JSON (sem chaves, PIN, rosto, memórias nem índice da câmera)."""
    from version import VERSION

    current = prefs.get_all()
    data = {k: current[k] for k in prefs._DEFAULTS if k in current and k not in EXPORT_EXCLUDE}
    return {"jarvis_settings": VERSION, "prefs": data}


class PrefsImportRequest(BaseModel):
    prefs: dict


@router.post("/api/prefs/import")
async def import_prefs(req: PrefsImportRequest) -> dict:
    """Aplica um arquivo exportado. Passa pelas mesmas validações do PATCH /api/prefs."""
    known = set(PrefsRequest.model_fields) - EXPORT_EXCLUDE
    data = {k: v for k, v in req.prefs.items() if k in known and v is not None}
    ignored = sorted(k for k in req.prefs if k not in data)
    if not data:
        raise HTTPException(status_code=400, detail="O arquivo não tem nenhuma preferência do JARVIS.")
    try:
        parsed = PrefsRequest(**data)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise HTTPException(status_code=400, detail=f"Valor inválido em {first['loc'][0]}.") from exc
    updated = await update_prefs(parsed)
    return {"applied": sorted(data), "ignored": ignored, "prefs": updated}
