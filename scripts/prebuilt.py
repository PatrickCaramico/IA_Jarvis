"""V8.2.2: baixa a INTERFACE PRONTA do JARVIS (frontend/dist) em vez de montar no PC.

Montar a interface no PC (npm run build) lê milhares de arquivos do node_modules; numa pasta do OneDrive e
com o antivírus olhando cada arquivo, isso levava minutos. O Netlify já monta a interface a cada versão nova
(em /pc/, a mesma do `npm run build`), com um files.json: a versão, a "impressão digital" do código da
interface (source_hash) e o sha256 de cada arquivo. Aqui:
1. calcula a impressão digital do código que está neste PC;
2. se for igual à do Netlify, baixa cada arquivo e confere o sha256;
3. troca a pasta dist de uma vez (se algo falhar, a antiga fica como estava).

Uso: python prebuilt.py [pasta-do-frontend]  -> sai com 0 se instalou, 1 se não deu (aí o .bat monta no PC).
Só biblioteca padrão (roda antes de qualquer dependência).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

BASE_URL = os.getenv("JARVIS_PREBUILT_URL", "https://projeto-jarvis-ia.netlify.app/pc/")
SOURCES = ["src", "public", "index.html", "package.json", "package-lock.json", "vite.config.js",
           "tailwind.config.js", "postcss.config.js"]
TIMEOUT = 20
MAX_FILE = 15 * 1024 * 1024


def _files(frontend: Path) -> list[Path]:
    out = []
    for name in SOURCES:
        p = frontend / name
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".") and f.name != "Thumbs.db")
    return out


def source_hash(frontend: Path) -> str:
    """Impressão digital do código da interface (igual à do scripts/netlify/manifest.mjs). CRLF vira LF."""
    h = hashlib.sha256()
    for f in sorted(_files(frontend), key=lambda x: x.relative_to(frontend).as_posix()):
        h.update(f.relative_to(frontend).as_posix().encode("utf-8") + b"\0")
        h.update(f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-atualizador", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 - endereço fixo do site do JARVIS
        return r.read(MAX_FILE + 1)


def fetch(frontend: Path, base_url: str = BASE_URL, get=_get, log=print, wait_s: float = 0, sleep=time.sleep) -> bool:
    """wait_s: logo depois de uma versão nova o site leva 1 a 3 min para ficar pronto; espera até esse tempo."""
    frontend = Path(frontend)
    local = source_hash(frontend)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            manifest = json.loads(get(base_url.rstrip("/") + "/files.json?t=" + str(int(time.time()))).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            log(f"  Interface pronta indisponível ({exc}).")
            return False
        if manifest.get("source_hash") == local:
            break
        if time.monotonic() >= deadline:
            log("  A interface pronta do site ainda é de outra versão: montando aqui mesmo.")
            return False
        log("  O site ainda está preparando a versão nova: esperando…")
        sleep(15)
    files = manifest.get("arquivos") or []
    dist, tmp = frontend / "dist", frontend / "dist.novo"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for item in files:
            rel = str(item["p"])
            if rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
                raise ValueError(f"caminho inválido: {rel}")
            data = get(base_url.rstrip("/") + "/" + rel)
            if len(data) > MAX_FILE or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError(f"arquivo diferente do esperado: {rel}")
            dest = tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if not (tmp / "index.html").exists():
            raise ValueError("sem index.html")
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp, ignore_errors=True)
        log(f"  Não consegui baixar a interface pronta ({exc}): montando aqui mesmo.")
        return False
    old = frontend / "dist.antigo"
    shutil.rmtree(old, ignore_errors=True)
    if dist.exists():
        dist.rename(old)
    tmp.rename(dist)
    shutil.rmtree(old, ignore_errors=True)
    now = time.time()
    os.utime(dist / "index.html", (now, now))  # mais nova que o código: o --stale vê que está em dia
    log(f"  Interface pronta baixada ({len(files)} arquivos, versão {manifest.get('versao', '?')}).")
    return True


if __name__ == "__main__":
    fe = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "frontend"
    sys.exit(0 if fetch(fe, wait_s=float(os.getenv("JARVIS_PREBUILT_WAIT", "60"))) else 1)
