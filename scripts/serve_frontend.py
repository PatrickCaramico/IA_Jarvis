"""Servidor leve da interface já compilada (frontend/dist) na porta 5173. V4.4.

Substitui o `npm run dev` no uso do dia a dia: não precisa do Node rodando nem compilar nada ao
abrir, então a página carrega quase na hora. Continua na mesma porta e endereço de antes
(http://127.0.0.1:5173), assim as permissões de câmera/microfone e as preferências salvas no
navegador continuam valendo. Para desenvolver com recarga ao vivo, use Iniciar-JARVIS-Dev.bat.

Uso:
    python serve_frontend.py [--host 127.0.0.1] [--port 5173]
    python serve_frontend.py --stale   # sai com 1 se o build estiver faltando ou desatualizado
"""
import argparse
import os
import ssl
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
DIST = FRONTEND / "dist"
# V7.7: https na rede de casa (ligado em Configurações > Segurança; o certificado é criado pelo backend)
TLS_DIR = Path(__file__).resolve().parent.parent / "data" / "tls"
HTTPS_PORT = 5443


def https_on() -> bool:
    env = os.getenv("JARVIS_HTTPS", "").strip().lower()
    if env in {"0", "false", "no", "off"}:
        return False
    if env in {"1", "true", "yes", "on"}:
        return True
    return (TLS_DIR / "https-ligado").exists()

# Arquivos cuja mudança pede um build novo.
SOURCES = ["src", "public", "index.html", "package.json", "vite.config.js", "tailwind.config.js", "postcss.config.js"]

# No Windows o tipo dos arquivos vem do registro e às vezes o .js sai como text/plain,
# o que faz o navegador recusar o script. Por isso os tipos são fixados aqui.
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".woff2": "font/woff2",
    ".wasm": "application/wasm",
    ".txt": "text/plain; charset=utf-8",
}


def newest_source_mtime() -> float:
    newest = 0.0
    for name in SOURCES:
        path = FRONTEND / name
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
        elif path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    newest = max(newest, f.stat().st_mtime)
    return newest


def is_stale() -> bool:
    index = DIST / "index.html"
    if not index.exists():
        return True
    return newest_source_mtime() > index.stat().st_mtime


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **MIME}

    redirect_https = False  # V7.7: no http, aparelho da rede vai para o https

    def send_head(self):
        if self.redirect_https and self.client_address[0] not in ("127.0.0.1", "::1"):
            host = (self.headers.get("Host") or "").split(":")[0] or "localhost"
            self.send_response(302)
            self.send_header("Location", f"https://{host}:{HTTPS_PORT}{self.path}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        # Página única: qualquer caminho que não seja arquivo cai no index.html.
        path = Path(self.translate_path(self.path))
        if not path.exists() or (path.is_dir() and not (path / "index.html").exists()):
            self.path = "/index.html"
        return super().send_head()

    def end_headers(self):
        # Arquivos em /assets/ têm hash no nome: podem ficar no cache. O index.html nunca.
        if self.path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):  # silencioso (roda escondido)
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--stale", action="store_true")
    args = parser.parse_args()

    if args.stale:
        return 1 if is_stale() else 0
    if not (DIST / "index.html").exists():
        print("frontend/dist não existe. Rode: npm run build (na pasta frontend).", file=sys.stderr)
        return 2

    crt, key = TLS_DIR / "jarvis-pc.crt", TLS_DIR / "jarvis-pc.key"
    use_https = https_on() and args.host not in ("127.0.0.1", "localhost") and crt.exists() and key.exists()
    if use_https:
        Handler.redirect_https = True
        secure = ThreadingHTTPServer((args.host, HTTPS_PORT), partial(Handler, directory=str(DIST)))
        secure.daemon_threads = True
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(str(crt), str(key))
        secure.socket = ctx.wrap_socket(secure.socket, server_side=True)

        class Plain(Handler):  # o servidor https não redireciona a si mesmo
            redirect_https = False

        secure.RequestHandlerClass = partial(Plain, directory=str(DIST))
        threading.Thread(target=secure.serve_forever, daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(DIST)))
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
