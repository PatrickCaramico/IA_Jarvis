"""V7.7: sobe o backend do JARVIS. Com https ligado (Configurações > Segurança), atende a rede de casa também
em https na porta 8443, no MESMO processo (mesmo estado, mesmos timers): a porta 8000 continua para este PC e
para as páginas públicas (baixar o app e o certificado); a chave de acesso não é aceita por http na rede.

Uso (o Iniciar-JARVIS.bat chama assim):  python run_server.py --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import argparse
import asyncio
import logging

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    asyncio.run(serve(args.host, args.port))


if __name__ == "__main__":
    main()
