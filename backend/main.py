"""Servidor FastAPI do JARVIS v4.2: composição do app.

O código foi dividido por área (refatoração 4.2):
- core/: estado, fala, tarefas de fundo, motor de conversa e cartões reativos;
- routes/: uma APIRouter por área (acesso, água, foco, integrações...).
Este arquivo só configura o log, o middleware de segurança, o CORS e inclui as rotas.
"""
import logging
import secrets
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from modules import access, reminders, tts

# Configuração de logging em console e arquivo rotativo
_file_handler = RotatingFileHandler(
    settings.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s: %(message)s"))
logging.basicConfig(
    level=logging.INFO,
    handlers=[_console_handler, _file_handler],
)
log = logging.getLogger("jarvis.main")

# Importados depois do log para que os módulos já usem a configuração acima.
from core import runtime, watchers  # noqa: E402
from core.runtime import ConnectionManager, manager  # noqa: E402,F401 - reexportados (testes, compatibilidade)
from routes import access as access_routes  # noqa: E402
from routes import fan, health, info, integrations, mobile, productivity, profile, profiles, search, system, water  # noqa: E402
from version import VERSION  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime.track_service(reminders.reminder_worker_loop())
    runtime.track_service(watchers.fan_watcher_loop())
    runtime.track_service(watchers.water_watcher_loop())
    runtime.track_service(watchers.triggers_watcher_loop())
    runtime.track_service(watchers.notifications_watcher_loop())
    runtime.track(tts.preload())  # V4.4: voz carrega depois que o servidor já está no ar
    yield
    for task in list(runtime.service_tasks):
        if not task.done():
            task.cancel()


app = FastAPI(title="JARVIS Assistant", version=VERSION, lifespan=lifespan)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host if request.client else ""
    is_local = client_ip in {"127.0.0.1", "::1", "localhost", "testclient"}

    if not is_local:
        if not settings.NETWORK_MODE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Acesso externo não permitido. O modo rede está desativado."},
            )
        token = request.headers.get("X-Jarvis-Token") or request.query_params.get("token")
        # V4.5: página de download do app e o APK abrem no celular antes do pareamento (sem token).
        # Não dão acesso a nada do JARVIS; o pareamento (/api/mobile/pair) continua exigindo o token.
        path = request.url.path.rstrip("/")
        no_token_ok = (request.method == "GET" and path in mobile.NO_TOKEN_PATHS) or (
            request.method == "POST" and path in mobile.NO_TOKEN_POST
        )
        if not no_token_ok and (not token or not secrets.compare_digest(token, runtime.ACCESS_TOKEN)):
            return JSONResponse(
                status_code=401,
                content={"detail": "Não autorizado. Token de acesso ausente ou inválido."},
            )

    # Bloqueio real (tela de bloqueio, Sentinela e modo visitante): rotas pessoais exigem acesso liberado.
    if not access.is_allowed(request.method, request.url.path):
        return JSONResponse(status_code=403, content=access.denial_detail())

    return await call_next(request)


# O CORS é registrado DEPOIS do middleware de segurança para ficar por fora dele: assim as
# respostas 401/403 (token, bloqueio, visitante) também levam os cabeçalhos CORS e o frontend
# consegue ler o motivo, em vez de receber um erro de rede.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(192\.168\.\d+\.\d+|10\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$",
    allow_methods=["*"],
    allow_headers=["*"],
)


for _module in (system, access_routes, profile, fan, water, search, productivity, info, integrations, health, mobile, profiles):
    app.include_router(_module.router)
