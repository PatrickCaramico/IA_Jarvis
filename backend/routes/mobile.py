"""V4.5: JARVIS no celular (app Android).

Fluxo:
1. Tela de bloqueio (Sentinela) mostra um QR pequeno -> http://IP:8000/api/mobile (página de
   download). Esse QR NÃO leva o token: quem só olhar a tela bloqueada consegue baixar o app, mas não
   consegue acessar o JARVIS.
2. Com a central liberada, "JARVIS no celular" > aba App mostra o QR de pareamento ->
   http://IP:8000/api/mobile/pair?token=... -> botão "Abrir no app JARVIS" (jarvis://connect?url=...).
3. O app guarda o endereço com o token e abre a central em tela cheia.

As duas primeiras páginas (download e APK) funcionam sem token na rede de casa (ver main.py), e só
existem com o modo rede ligado (Iniciar-JARVIS-Rede.bat).
"""

import asyncio
import json
import secrets
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from config import settings
from core import runtime
from routes.system import local_ip
from version import VERSION

router = APIRouter()

APK_PATH = Path(__file__).resolve().parents[2] / "mobile" / "dist" / "JARVIS.apk"
PACKAGE = "com.patrick.jarvis"

# Rotas que o celular usa ANTES de ter o token (liberadas no middleware de main.py, só no modo rede)
NO_TOKEN_PATHS = {"/api/mobile", "/api/mobile/app.apk"}
NO_TOKEN_POST = {"/api/mobile/pair-pin"}  # pareamento pelo PIN do dono (é como o celular ganha a chave)


def apk_available() -> bool:
    return APK_PATH.exists() and APK_PATH.stat().st_size > 0


def apk_version() -> str:
    """V5.6: versão do APK gerado (arquivo JARVIS.apk.version ao lado dele).

    O app compara com a dele para decidir se atualiza. Antes o PC mandava a versão do JARVIS inteiro, e o
    celular se atualizava a cada mudança do PC, mesmo sem o app ter mudado (ou ficava tentando de novo
    quando o APK era mais antigo que o JARVIS). Sem o arquivo (APK antigo), usa a versão do JARVIS.
    """
    try:
        side = APK_PATH.with_name(APK_PATH.name + ".version")
        text = side.read_text(encoding="ascii").strip()
        if text:
            return text
    except (OSError, AttributeError, ValueError):
        pass
    return VERSION


@router.get("/api/mobile/info")
async def mobile_info() -> dict:
    """Pública (tela de bloqueio): dá o QR de download, sem token."""
    ip = local_ip()
    return {
        "available": apk_available(),
        "network_mode": settings.NETWORK_MODE,
        "download_url": f"http://{ip}:8000/api/mobile" if ip else "",
        "version": apk_version(),
        "size_kb": round(APK_PATH.stat().st_size / 1024) if apk_available() else 0,
    }


_PAGE = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;font-family:system-ui,sans-serif;color:#e6f7fb;padding:28px 20px 40px;
background:linear-gradient(rgba(205,235,255,.17) 1px,transparent 1px) 0 0/100px 100px,linear-gradient(90deg,rgba(205,235,255,.17) 1px,transparent 1px) 0 0/100px 100px,
linear-gradient(rgba(190,225,255,.075) 1px,transparent 1px) 0 0/20px 20px,linear-gradient(90deg,rgba(190,225,255,.075) 1px,transparent 1px) 0 0/20px 20px,
radial-gradient(ellipse 80% 70% at 50% 30%,#2362b8,#174a95 55%,#0d3170);background-attachment:fixed}}
.b{{text-align:center;margin:6px 0 22px}}.o{{width:84px;height:84px;margin:0 auto 12px;border-radius:50%;
background:radial-gradient(circle,#fff 0%,#c9f6ff 22%,#4fdcff 55%,#0a9fd6 100%);box-shadow:0 0 0 9px rgba(2,12,34,.85),0 0 0 10px rgba(160,230,255,.3),0 0 50px 18px rgba(79,220,255,.45)}}
h1{{margin:0;letter-spacing:.28em;font-size:1.45rem}}.s{{margin-top:6px;font-size:.7rem;letter-spacing:.2em;color:rgba(225,242,255,.72)}}
.c{{background:linear-gradient(180deg,rgba(6,26,62,.84),rgba(3,14,38,.92));border:1px solid rgba(200,235,255,.28);border-radius:14px;padding:18px;margin:0 auto 14px;max-width:460px}}
.c h2{{margin:0 0 10px;font-size:.76rem;letter-spacing:.2em;color:#22d3ee}}ol{{margin:0;padding-left:20px;line-height:1.55}}li{{margin-bottom:6px}}
a.btn{{display:block;text-align:center;text-decoration:none;margin-top:12px;padding:14px;border-radius:10px;font-weight:700;letter-spacing:.14em;font-size:.8rem;
color:#fff;background:rgba(34,211,238,.22);border:1px solid rgba(79,220,255,.75)}}a.alt{{background:transparent;border-color:rgba(200,235,255,.35);font-weight:500}}
.m{{color:rgba(225,242,255,.72);font-size:.8rem;line-height:1.5}}b{{color:#fff}}.w{{border-color:rgba(251,191,36,.7)}}.w h2{{color:#fbbf24}}
</style></head><body><div class="b"><div class="o"></div><h1>JARVIS</h1><div class="s">{sub}</div></div>{body}</body></html>"""


@router.get("/api/mobile", response_class=HTMLResponse)
async def mobile_page(request: Request) -> HTMLResponse:
    """Página que abre ao escanear o QR do bloqueio: baixar o app e como conectar."""
    if apk_available():
        size = round(APK_PATH.stat().st_size / 1024)
        download = (
            '<div class="c"><h2>1 · INSTALAR O APP</h2>'
            f'<a class="btn" href="/api/mobile/app.apk" download="JARVIS.apk">BAIXAR JARVIS.apk · v{escape(apk_version())} · {size} KB</a>'
            '<p class="m">Ao abrir o arquivo, o Android pede para <b>permitir instalar apps desta fonte</b> '
            '(o navegador). Permita só desta vez. O app é o seu JARVIS: não vem da Play Store porque é feito para '
            'este PC.</p></div>'
        )
    else:
        download = (
            '<div class="c w"><h2>APP AINDA NÃO GERADO</h2><p class="m">No PC, rode <b>Gerar-App-Android.bat</b> '
            'e escaneie de novo.</p></div>'
        )
    host = request.url.hostname or local_ip()
    open_intent = f"intent://setup?host={quote(host)}#Intent;scheme=jarvis;package={PACKAGE};end"
    open_deep = f"jarvis://setup?host={quote(host)}"
    # V5.1.1: app já instalado? O QR abre o app (que se atualiza sozinho). Sem o app, o mesmo botão baixa o APK.
    base = f"http://{host}:8000"
    open_or_download = (
        f"intent://open?host={quote(host)}#Intent;scheme=jarvis;package={PACKAGE};"
        f"S.browser_fallback_url={quote(base + '/api/mobile/app.apk', safe='')};end"
    )
    # Tentativa automática ao abrir a página: sem o app, volta para esta página (?app=0) sem baixar nada.
    auto_open = (
        f"intent://open?host={quote(host)}#Intent;scheme=jarvis;package={PACKAGE};"
        f"S.browser_fallback_url={quote(base + '/api/mobile?app=0', safe='')};end"
    )
    tried = request.query_params.get("app") == "0"
    quick = (
        '<div class="c"><h2>JÁ TEM O APP NO CELULAR?</h2>'
        f'<a class="btn" href="{escape(open_or_download)}">ABRIR O JARVIS</a>'
        '<p class="m">Abre o app direto. Se o PC tiver uma versão nova, <b>o app se atualiza sozinho</b>: '
        'não precisa baixar de novo. Sem o app instalado, este botão baixa o JARVIS.apk.</p></div>'
    ) if apk_available() else ""
    auto = "" if tried or not apk_available() else (
        "<script>if(/Android/i.test(navigator.userAgent)){setTimeout(function(){location.href="
        f"{json.dumps(auto_open)};}},300);}}</script>"
    )
    body = quick + download + (
        '<div class="c"><h2>2 · ABRIR E ENTRAR</h2>'
        f'<a class="btn" href="{escape(open_intent)}">ABRIR O JARVIS</a>'
        f'<a class="btn alt" href="{escape(open_deep)}">Não abriu? Tentar de outro jeito</a>'
        '<p class="m">Depois de instalar, toque em <b>ABRIR O JARVIS</b> aqui. O app já sabe o endereço deste PC '
        f'(<b>{escape(host)}</b>): é só digitar o <b>PIN</b> do perfil principal.</p>'
        '<p class="m">A chave de acesso fica só no seu celular. Nada vai para a internet: funciona na mesma Wi-Fi do PC.</p></div>'
    )
    return HTMLResponse(_PAGE.format(title="JARVIS no celular", sub="CENTRAL PESSOAL NO CELULAR", body=body + auto))


@router.get("/api/mobile/app.apk")
async def mobile_apk():
    if not apk_available():
        return HTMLResponse("App ainda não gerado. Rode Gerar-App-Android.bat no PC.", status_code=404)
    return FileResponse(APK_PATH, media_type="application/vnd.android.package-archive", filename="JARVIS.apk")


class PairPinRequest(BaseModel):
    pin: str


@router.post("/api/mobile/pair-pin")
async def mobile_pair_pin(req: PairPinRequest, request: Request) -> dict:
    """Pareia o app digitando o PIN do perfil principal (V4.5). Devolve o endereço com a chave.

    Funciona sem a chave (é o jeito de obtê-la), só no modo rede, e conta no mesmo limite de
    tentativas do PIN. Sem PIN cadastrado no PC, não pareia (senão qualquer um na Wi-Fi entraria).
    """
    from modules import lock_pin, profiles

    owner_pin = profiles._base(profiles.OWNER_ID) / "lock_pin.json"  # noqa: SLF001
    if not owner_pin.exists():
        raise HTTPException(status_code=403, detail="Crie um PIN no PC (Configurações › Bloqueio) para parear o celular.")
    previous = lock_pin.PIN_PATH
    try:
        lock_pin.PIN_PATH = owner_pin
        result = await asyncio.to_thread(lock_pin.verify, req.pin)
    finally:
        lock_pin.PIN_PATH = previous
    if not result.get("verified"):
        detail = ("PIN bloqueado por excesso de tentativas. Espere alguns minutos."
                  if result.get("reason") == "locked_out"
                  else f"PIN incorreto. Restam {result.get('remaining_attempts', 0)} tentativas.")
        raise HTTPException(status_code=403, detail=detail)
    ip = request.url.hostname or local_ip()
    return {"url": f"http://{ip}:5173/?token={runtime.ACCESS_TOKEN}"}


@router.get("/api/mobile/notifications")
async def mobile_notifications(request: Request, since: int = -1) -> dict:
    """Avisos para o app Android (lembretes, água, gatilhos, Modo Torcedor).

    Sempre exige a chave de pareamento, mesmo do próprio PC e com a central bloqueada: o conteúdo é
    pessoal e só vai para o celular pareado. since=-1: só devolve o número do último aviso (o app
    começa dali, sem receber avisos antigos de uma vez).
    """
    token = request.headers.get("X-Jarvis-Token") or request.query_params.get("token") or ""
    if not secrets.compare_digest(token, runtime.ACCESS_TOKEN):
        raise HTTPException(status_code=401, detail="Chave de pareamento ausente ou inválida.")
    feed = runtime.notifications_since(max(since, 0))
    if since < 0:
        return {"items": [], "latest": feed["latest"]}
    return feed


@router.get("/api/mobile/pair", response_class=HTMLResponse)
async def mobile_pair(request: Request) -> HTMLResponse:
    """Página de pareamento (exige o token, que já veio no QR da central liberada).

    V5.4: abre o app sozinha, já pareado (sem PIN e sem digitar o endereço). Sem o app instalado, o
    Android volta para esta página (?app=0), que oferece baixar o JARVIS.apk e escanear de novo.
    """
    ip = request.url.hostname or local_ip()
    target = f"http://{ip}:5173/?token={runtime.ACCESS_TOKEN}"
    deep = f"jarvis://connect?url={quote(target, safe='')}"
    intent = f"intent://connect?url={quote(target, safe='')}#Intent;scheme=jarvis;package={PACKAGE};end"
    self_url = f"http://{ip}:8000/api/mobile/pair?token={runtime.ACCESS_TOKEN}&app=0"
    auto_intent = (f"intent://connect?url={quote(target, safe='')}#Intent;scheme=jarvis;package={PACKAGE};"
                   f"S.browser_fallback_url={quote(self_url, safe='')};end")
    no_app = request.query_params.get("app") == "0"
    install = (
        '<div class="c w"><h2>1 · INSTALE O APP</h2>'
        '<a class="btn" href="/api/mobile/app.apk" download="JARVIS.apk">BAIXAR JARVIS.apk</a>'
        '<p class="m">Instale o app e <b>escaneie este mesmo QR de novo</b>: ele abre o JARVIS já conectado, sem PIN.</p></div>'
    ) if no_app and apk_available() else ""
    body = install + (
        f'<div class="c"><h2>{"2 · " if install else ""}PAREAR ESTE CELULAR</h2>'
        f'<a class="btn" href="{escape(intent)}">ABRIR NO APP JARVIS</a>'
        f'<a class="btn alt" href="{escape(deep)}">Não abriu? Tentar de outro jeito</a>'
        f'<a class="btn alt" href="{escape(target)}">Continuar no navegador</a>'
        '<p class="m">O app entra já conectado a este PC: não precisa digitar endereço nem PIN.</p></div>'
    )
    auto = "" if no_app else (
        "<script>if(/Android/i.test(navigator.userAgent)){setTimeout(function(){location.href="
        f"{json.dumps(auto_intent)};}},300);}}</script>"
    )
    return HTMLResponse(_PAGE.format(title="Parear JARVIS", sub="PAREAMENTO NA REDE DE CASA", body=body + auto))
