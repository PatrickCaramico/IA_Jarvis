"""Rotas de informação: notícias, sistema, volume, clima, finanças e fontes de dados."""

import logging
import asyncio
from fastapi import HTTPException, Query
from pydantic import BaseModel
from config import settings
from modules import tools, system_monitor, system_control, google_calendar, spotify
from modules import news_radar
from fastapi import APIRouter
from services import quotes

log = logging.getLogger("jarvis.info")
router = APIRouter()


@router.get("/api/news")
async def get_news(category: str = "tecnologia", limit: int = 8) -> dict:
    """Radar de notícias do HUD: destaques por categoria (RSS do Google News)."""
    try:
        items = await asyncio.to_thread(news_radar.fetch_news_by_category, category, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Falha ao carregar notícias")
        raise HTTPException(status_code=502, detail="Não consegui carregar as notícias agora.") from exc
    return {"category": category, "items": items}


class VolumeRequest(BaseModel):
    level: int


@router.get("/api/system")
async def get_system_status() -> dict:
    snapshot = await asyncio.to_thread(system_monitor.snapshot)  # psutil mede a CPU por 0,15 s
    snapshot["volume"] = await asyncio.to_thread(system_control._get_volume)
    return snapshot


@router.patch("/api/system/volume")
async def set_system_volume(req: VolumeRequest) -> dict:
    if not 0 <= req.level <= 100:
        raise HTTPException(status_code=400, detail="O volume deve estar entre 0 e 100.")
    try:
        await asyncio.to_thread(system_control._set_volume, req.level)
        volume = await asyncio.to_thread(system_control._get_volume)
    except Exception as exc:
        log.exception("Falha ao ajustar volume do sistema")
        raise HTTPException(status_code=502, detail="Não consegui ajustar o volume do sistema.") from exc
    # Algumas versões do Windows não expõem a leitura do endpoint, embora a
    # escrita tenha sido aplicada. Nesse caso, devolvemos o valor solicitado.
    return {
        "status": "ok",
        "volume": volume if volume >= 0 else req.level,
        "readback": volume >= 0,
    }


@router.get("/api/weather")
async def get_weather(city: str | None = Query(default=None, max_length=80)) -> dict:
    """Retorna dados estruturados para o widget de clima."""
    requested_city = (city or settings.WEATHER_CITY).strip()
    if not requested_city:
        raise HTTPException(status_code=400, detail="Informe uma cidade para consultar o clima.")
    try:
        result = await asyncio.to_thread(tools._fetch_weather, requested_city)
    except Exception as exc:
        log.warning("Falha ao consultar clima para %s: %s", requested_city, exc)
        raise HTTPException(status_code=502, detail="Não consegui consultar o clima agora.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Não encontrei a cidade {requested_city}.")
    data, place = result["data"], result["place"]
    current, daily = data.get("current", {}), data.get("daily", {})
    try:
        probability = (daily.get("precipitation_probability_max") or [None])[0]
        return {
            "place": place,
            "temperature": round(current["temperature_2m"]),
            "apparent_temperature": round(current["apparent_temperature"]),
            "description": tools._WMO.get(current.get("weather_code"), "tempo variável"),
            "maximum": round(daily["temperature_2m_max"][0]),
            "minimum": round(daily["temperature_2m_min"][0]),
            "rain_probability": round(probability) if probability is not None else None,
        }
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        log.warning("Resposta de clima incompleta para %s: %s", requested_city, exc)
        raise HTTPException(status_code=502, detail="A previsão retornou dados incompletos.") from exc


class ExpenseRequest(BaseModel):
    kind: str = "out"  # "out" (gasto) | "in" (entrada)
    amount: float
    desc: str = ""


@router.get("/api/finance/expenses")
async def finance_expenses(period: str = "month") -> dict:
    """V4.5: gastos e entradas que você contou ao JARVIS (sem banco), por período."""
    from modules import finances

    if period not in {"today", "yesterday", "week", "month"}:
        period = "month"
    return finances.summary(period)


@router.post("/api/finance/expenses")
async def add_expense(req: ExpenseRequest) -> dict:
    from modules import finances

    if req.kind not in {"out", "in"} or not 0 < req.amount < 10_000_000:
        raise HTTPException(status_code=400, detail="Valor inválido.")
    item = finances.add(req.kind, req.amount, req.desc)
    return {"item": item, "summary": finances.summary("month")}


@router.get("/api/finance")
async def get_finance_data() -> dict:
    """Retorna cotações de moedas e mercado financeiro em tempo real (AwesomeAPI)."""
    rates = {}
    live = True
    try:
        raw = await asyncio.to_thread(quotes.fetch_rates)
        for item in quotes.summarize(raw):
            rates[item["pair"]] = {k: item[k] for k in ("name", "bid", "pctChange", "high", "low")}
    except Exception as exc:
        live = False
        log.warning("Falha ao consultar cotações financeiras: %s", exc)
        rates = {
            "USDBRL": {"name": "Dólar Comercial", "bid": 5.45, "pctChange": 0.12},
            "EURBRL": {"name": "Euro Comercial", "bid": 5.92, "pctChange": -0.08},
            "BTCBRL": {"name": "Bitcoin", "bid": 372000.0, "pctChange": 1.45},
        }
    # "live": False = valores de referência fixos (a consulta falhou), não cotação real
    return {"status": "ok", "rates": rates, "live": live}


@router.get("/api/datasources")
async def get_datasources() -> dict:
    """Catálogo unificado de fontes de dados e canais do JARVIS."""
    cal_conn = google_calendar.connected()
    return {
        "sources": [
            {
                "id": "calendar",
                "name": "Google Calendar",
                "category": "Produtividade",
                "status": "connected" if cal_conn else "available",
                "description": "Eventos e reuniões sincronizados.",
            },
            {
                "id": "weather",
                "name": "Open-Meteo",
                "category": "Sensores e Clima",
                "status": "connected",
                "description": "Previsão, sensação térmica e probabilidade de chuva.",
            },
            {
                "id": "news",
                "name": "Google News RSS",
                "category": "Comunicação",
                "status": "connected",
                "description": "Feed de notícias verificado por tópicos em tempo real.",
            },
            {
                "id": "finance",
                "name": "AwesomeAPI & brapi",
                "category": "Finanças",
                "status": "connected",
                "description": "Cotações de moedas, câmbio e índices de mercado.",
            },
            {
                "id": "spotify",
                "name": "Spotify Player",
                "category": "Comunicação",
                "status": "connected" if spotify.connected() else "available",
                "description": "Reprodução de músicas e podcasts no desktop.",
            },
            {
                "id": "bambu",
                "name": "Impressora 3D Bambu Lab",
                "category": "Casa e dispositivos",
                "status": "available",
                "description": "Protocolo MQTT local para monitorar impressões 3D.",
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp Bridge",
                "category": "Comunicação",
                "status": "available",
                "description": "Notificações e mensagens prioritárias (experimental).",
            },
        ]
    }
