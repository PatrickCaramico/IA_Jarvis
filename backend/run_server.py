"""V7.7: sobe o backend do JARVIS. Com https ligado (Configurações > Segurança), atende a rede de casa também
em https na porta 8443, no MESMO processo (mesmo estado, mesmos timers): a porta 8000 continua para este PC e
para as páginas públicas (baixar o app e o certificado); a chave de acesso não é aceita por http na rede.

Uso (o Iniciar-JARVIS.bat chama assim):  python run_server.py --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
import traceback
from pathlib import Path

import uvicorn

log = logging.getLogger("jarvis.run_server")


def build_servers(host: str, port: int) -> list[uvicorn.Server]:
    import main
    from modules import tls

    servers = [uvicorn.Server(uvicorn.Config(main.app, host=host, port=port, lifespan="on"))]
    if tls.enabled() and host not in ("127.0.0.1", "localhost"):
        try:
            paths = tls.ensure()
            servers.append(uvicorn.Server(uvicorn.Config(
                main.app, host=host, port=tls.API_HTTPS_PORT, lifespan="off",
                ssl_keyfile=str(paths["key"]), ssl_certfile=str(paths["crt"]))))
            log.info("https ligado: rede de casa em https://%s:%d", host, tls.API_HTTPS_PORT)
        except Exception:  # noqa: BLE001 - sem certificado, sobe só o http (e o Diagnóstico avisa)
            log.exception("Não consegui ligar o https; seguindo só com http.")
    for extra in servers[1:]:
        extra.install_signal_handlers = lambda: None  # o primeiro servidor cuida do Ctrl+C
    return servers


async def serve(host: str, port: int) -> None:
    servers = build_servers(host, port)
    await asyncio.gather(*(s.serve() for s in servers))


def main() -> None:
    # V8.7.2: ligar o JARVIS (carregar os modelos) é pesado: começa em prioridade baixa e o próprio JARVIS volta
    # para a normal uns segundos depois de ligado (main.lifespan)
    from core import priority

    priority.set_self("below")
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    asyncio.run(serve(args.host, args.port))


# V9.5.2: o backend sobe escondido (sem console). Antes, se ele caía ao ligar (biblioteca faltando depois de uma
# atualização, porta ocupada), o erro sumia: a central ficava "procurando" o PC e nada dizia o porquê. Agora o
# motivo fica em logs/backend-erro.log (o scripts/socorro_subida.py lê e resolve o que dá, como instalar o que falta).
CRASH_LOG = Path(__file__).resolve().parents[1] / "logs" / "backend-erro.log"


def record_crash(text: str, path: Path = CRASH_LOG) -> None:
    try:
        path.parent.mkdir(exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"\n===== {stamp} o JARVIS caiu ao ligar =====\n{text}\n")
    except OSError:
        pass


def run() -> int:
    try:
        main()
    except KeyboardInterrupt:
        return 0
    except SystemExit as exc:  # o uvicorn sai com 1 quando não consegue abrir a porta
        if exc.code not in (0, None):
            record_crash(f"Saiu com o código {exc.code} (porta 8000 ocupada ou erro ao abrir o servidor).")
        return int(exc.code or 0) if isinstance(exc.code, int) else 1
    except BaseException:  # noqa: BLE001 - qualquer outra queda: registra o motivo e sai com erro
        record_crash(traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
