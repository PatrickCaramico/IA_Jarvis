"""V8.0: JARVIS.exe (app para Windows com a ilha no topo). O executável é gerado no PC pelo Gerar-App-Windows.bat
(PyInstaller + pywebview) e fica em data/desktop/JARVIS.exe; o botão ⬇ APP PARA WINDOWS baixa daqui.
Só a partir deste PC: o executável guarda o caminho da pasta do JARVIS e não serve para outro computador."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from config import settings
from core import runtime

router = APIRouter()
EXE = settings.DATA_DIR / "desktop" / "JARVIS.exe"


@router.get("/api/desktop/info")
async def desktop_info(request: Request) -> dict:
    ok = EXE.exists()
    return {
        "disponivel": ok and runtime.is_local_conn(request),
        "gerado": ok,
        "local": runtime.is_local_conn(request),
        "tamanho_mb": round(EXE.stat().st_size / 1_048_576, 1) if ok else None,
        "gerado_em": time.strftime("%d/%m/%Y %H:%M", time.localtime(EXE.stat().st_mtime)) if ok else None,
        "como_gerar": "Na pasta do JARVIS, dê dois cliques em Gerar-App-Windows.bat (uma vez; leva uns minutos).",
    }


@router.get("/api/desktop/app")
async def desktop_app(request: Request):
    if not runtime.is_local_conn(request):
        raise HTTPException(status_code=403, detail="O JARVIS.exe é baixado no próprio PC do JARVIS.")
    if not EXE.exists():
        raise HTTPException(status_code=404, detail="O JARVIS.exe ainda não foi gerado. Rode Gerar-App-Windows.bat.")
    return FileResponse(EXE, media_type="application/vnd.microsoft.portable-executable", filename="JARVIS.exe")
