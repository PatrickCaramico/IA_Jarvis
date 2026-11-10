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
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
DIST = FRONTEND / "dist"

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

    def send_head(self):
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

    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(DIST)))
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
