"""App do JARVIS para Windows (janela própria + ilha no topo + tecla para falar).

V8.1.1: não existe mais JARVIS.exe para baixar. O exe do PyInstaller (8.0) era acusado como vírus pelo McAfee
(falso positivo). Agora o Gerar-App-Windows.bat cria um atalho "JARVIS" que abre o app com o pythonw.exe oficial
do Python (assinado). O instalador grava data/desktop/app.json; daqui dá para ver se já foi instalado e abrir o app.
"""
from __future__ import annotations

import json
import os
import sys

from fastapi import APIRouter, HTTPException, Request

from config import settings
from core import runtime

router = APIRouter()
MARK = settings.DATA_DIR / "desktop" / "app.json"
OLD_EXE = settings.DATA_DIR / "desktop" / "JARVIS.exe"
HOW = "Na pasta do JARVIS, dê dois cliques em Gerar-App-Windows.bat (uma vez; leva uns minutos)."


def _mark() -> dict | None:
    try:
        data = json.loads(MARK.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


@router.get("/api/desktop/info")
async def desktop_info(request: Request) -> dict:
    mark = _mark()
    local = runtime.is_local_conn(request)
    return {
        "instalado": bool(mark), "local": local, "versao": (mark or {}).get("versao"),
        "instalado_em": (mark or {}).get("instalado_em"), "exe_antigo": OLD_EXE.exists(), "como_instalar": HOW,
    }


@router.post("/api/desktop/open")
async def desktop_open(request: Request) -> dict:
    """Abre o app pelo atalho (só no próprio PC do JARVIS)."""
    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="O app abre no próprio PC do JARVIS.")
    lnk = (_mark() or {}).get("atalho") or ""
    if not lnk or not os.path.exists(lnk):
        raise HTTPException(status_code=404, detail="O app ainda não foi instalado. " + HOW)
    if sys.platform != "win32":
        raise HTTPException(status_code=501, detail="O app é para Windows.")
    os.startfile(lnk)  # type: ignore[attr-defined]  # noqa: S606 - atalho criado pelo próprio instalador
    return {"ok": True}


@router.get("/api/desktop/app")
async def desktop_app() -> dict:
    raise HTTPException(status_code=410, detail="Não há mais JARVIS.exe para baixar (o antivírus acusava). " + HOW)
