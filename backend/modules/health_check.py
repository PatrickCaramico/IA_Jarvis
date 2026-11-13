"""V7.4: 🩺 DIAGNÓSTICO (botão na tela de bloqueio, em CONTROLES e no perfil; ou "Jarvis, roda um diagnóstico").

Testa DE VERDADE as peças do JARVIS no PC e devolve uma lista simples: ok / atenção / falha, com o que fazer.
- IA: manda uma pergunta mínima e mede o tempo (no máximo 1 vez por minuto, para não gastar cota);
- voz: gera um áudio curto (sem tocar) e mede o tempo;
- internet, nuvem (sincronização com o celular), disco, arquivos de dados, erros recentes e versão.
Nada pessoal sai daqui (a tela de bloqueio também pode rodar o diagnóstico).
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from config import settings
from version import VERSION

OK, WARN, FAIL = "ok", "warn", "fail"
AI_CACHE_SECONDS = 60
_ai_cache: dict = {}


def _item(id_: str, label: str, status: str, detail: str, fix: str = "", ms: int | None = None) -> dict:
    return {"id": id_, "label": label, "status": status, "detail": detail, "fix": fix if status != OK else "", "ms": ms}


def _ai_configured() -> bool:
    return bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or settings.GEMINI_API_KEY)


async def check_ai() -> dict:
    if not _ai_configured():
        return _item("ai", "Inteligência artificial", FAIL, "Nenhuma chave de IA no .env.",
                     "Coloque GEMINI_API_KEY (grátis), OPENAI_API_KEY ou ANTHROPIC_API_KEY no arquivo .env da pasta JARVIS e reinicie.")
    now = time.monotonic()
    if _ai_cache and now - _ai_cache["at"] < AI_CACHE_SECONDS:
        return _ai_cache["item"]
    from services import llm_orchestrator

    in_cooldown, remaining = llm_orchestrator.get_quota_cooldown()
    if in_cooldown:
        item = _item("ai", "Inteligência artificial", WARN, f"Cota da IA em pausa ({remaining} s).",
                     "Espere um minuto. Se acontecer sempre, troque de chave/modelo em Configurações > IA.")
    else:
        started = time.monotonic()
        try:
            reply = await asyncio.wait_for(asyncio.to_thread(llm_orchestrator.ask_text, "Responda só com a palavra OK."), timeout=25)
            ms = int((time.monotonic() - started) * 1000)
            status = OK if reply and ms < 8000 else WARN
            item = _item("ai", "Inteligência artificial", status, f"Respondeu em {ms / 1000:.1f} s.",
                         "A IA está lenta: confira a internet ou use um modelo mais rápido (ex.: gemini-2.5-flash).", ms)
        except asyncio.TimeoutError:
            item = _item("ai", "Inteligência artificial", FAIL, "Não respondeu em 25 s.",
                         "Confira a internet e a chave da IA no .env (Configurações > IA mostra o provedor em uso).")
        except Exception as exc:  # noqa: BLE001
            item = _item("ai", "Inteligência artificial", FAIL, f"Erro: {str(exc)[:120]}",
                         "A chave pode estar errada ou sem crédito. Gere outra e coloque no .env.")
    _ai_cache.update(at=now, item=item)
    return item


async def check_voice() -> dict:
    from modules import tts

    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_diag_")
    os.close(fd)
    started = time.monotonic()
    try:
        await asyncio.wait_for(tts._synthesize("Diagnóstico da voz.", path), timeout=20)  # noqa: SLF001
        ms = int((time.monotonic() - started) * 1000)
        ok = Path(path).stat().st_size > 500
        return _item("voice", "Voz do JARVIS", OK if ok and ms < 4000 else WARN,
                     f"Áudio gerado em {ms / 1000:.1f} s." if ok else "Áudio veio vazio.",
                     "A voz depende da internet (vozes da Microsoft). Confira a conexão.", ms)
    except Exception as exc:  # noqa: BLE001
        reason = "sem conexão com o serviço de voz" if "connect" in str(exc).lower() else str(exc).split(" ssl:")[0][:100]
        return _item("voice", "Voz do JARVIS", FAIL, f"Não gerou a voz ({reason}).",
                     "Confira a internet. Se persistir, feche e abra o JARVIS (Parar-JARVIS.bat e Iniciar-JARVIS.bat).")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def check_internet() -> dict:
    started = time.monotonic()
    try:
        requests.get("https://www.google.com/generate_204", timeout=5)
        ms = int((time.monotonic() - started) * 1000)
        return _item("internet", "Internet do PC", OK if ms < 1500 else WARN, f"Conectado ({ms} ms).",
                     "A internet está lenta: isso deixa a IA e a voz lentas.", ms)
    except Exception:  # noqa: BLE001
        return _item("internet", "Internet do PC", FAIL, "Sem internet.",
                     "Confira o Wi-Fi/cabo do PC. Sem internet, a IA, a voz e o clima não funcionam.")


def check_cloud() -> dict:
    from modules import cloud_sync

    if not cloud_sync.enabled():
        return _item("cloud", "Modo nuvem (celular fora de casa)", WARN, "Desligado (sem JARVIS_NUVEM_CHAVE no .env).",
                     "Para usar o JARVIS no celular fora de casa, siga docs/MODO-NUVEM.md.")
    st = cloud_sync.STATE
    if st.get("last_error"):
        return _item("cloud", "Modo nuvem (celular fora de casa)", FAIL, f"Última sincronização falhou: {st['last_error'][:100]}",
                     "Confira a internet e se a JARVIS_NUVEM_CHAVE do .env é a mesma do Netlify.")
    if st.get("last_ok"):
        return _item("cloud", "Modo nuvem (celular fora de casa)", OK, f"Sincronizado às {st['last_ok'][-5:]}.")
    return _item("cloud", "Modo nuvem (celular fora de casa)", WARN, "Ainda não sincronizou desde que o JARVIS ligou.",
                 "Espere 1 minuto e rode o diagnóstico de novo.")


def check_disk() -> dict:
    try:
        free = shutil.disk_usage(str(settings.DATA_DIR)).free / 1_073_741_824
    except OSError:
        return _item("disk", "Espaço em disco", WARN, "Não consegui medir.")
    if free < 0.5:
        return _item("disk", "Espaço em disco", FAIL, f"Só {free:.1f} GB livres.", "Libere espaço no disco: o JARVIS precisa gravar dados e áudio.")
    if free < 2:
        return _item("disk", "Espaço em disco", WARN, f"{free:.1f} GB livres.", "Está ficando pouco espaço; libere alguns GB.")
    return _item("disk", "Espaço em disco", OK, f"{free:.0f} GB livres.")


def check_data(data_dir: Path | None = None) -> dict:
    base = Path(data_dir or settings.DATA_DIR)
    bad = []
    files = list(base.rglob("*.json")) if base.exists() else []
    for f in files:
        try:
            json.loads(f.read_text(encoding="utf-8") or "null")
        except (OSError, ValueError):
            bad.append(f.name)
    if bad:
        return _item("data", "Arquivos de dados", FAIL, f"{len(bad)} arquivo(s) danificado(s): {', '.join(bad[:3])}",
                     "Rode o Backup-Dados.bat e me mande o nome do arquivo; dá para restaurar de um backup.")
    return _item("data", "Arquivos de dados", OK, f"{len(files)} arquivos íntegros.")


def check_errors(now: datetime | None = None) -> dict:
    from modules import event_log

    now = now or datetime.now()
    since = now - timedelta(hours=24)
    recent = []
    for e in event_log.list_events(200):
        try:
            if e.get("kind") == "error" and datetime.fromisoformat(e.get("at", "")) >= since:
                recent.append(e)
        except ValueError:
            continue
    if not recent:
        return _item("errors", "Erros nas últimas 24 h", OK, "Nenhum.")
    last = recent[0].get("message", "")[:90]
    return _item("errors", "Erros nas últimas 24 h", WARN if len(recent) < 5 else FAIL, f"{len(recent)} erro(s). Último: {last}",
                 "Veja os detalhes em TELAS > Relatório de logs (ou Ver-Logs.bat no PC).")


async def run() -> dict:
    started = time.monotonic()
    ai, voice, internet = await asyncio.gather(check_ai(), check_voice(), asyncio.to_thread(check_internet))
    items = [
        _item("backend", "Servidor do JARVIS (PC)", OK, f"No ar, versão {VERSION}."),
        ai, voice, internet,
        await asyncio.to_thread(check_cloud),
        await asyncio.to_thread(check_disk),
        await asyncio.to_thread(check_data),
        await asyncio.to_thread(check_errors),
    ]
    return {"version": VERSION, "items": items, "took_ms": int((time.monotonic() - started) * 1000),
            "at": datetime.now().strftime("%d/%m %H:%M")}
