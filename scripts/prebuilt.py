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

V8.3.1: no PC do Patrick a interface pronta nunca chegava. Agora:
- se o Python não conseguir baixar (o antivírus corta a conexão segura dele: "SSL EOF" no log), baixa pelo
  curl.exe do próprio Windows, que usa a mesma conexão do navegador;
- se o código deste PC for o MESMO commit que o site montou (files.json traz o "commit"), vale mesmo que algum
  arquivo tenha mudado no PC (ex.: o npm install mexe no package-lock.json);
- tudo vai para logs/prebuilt.log (antes as mensagens sumiam com a janela escondida).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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


def _get_python(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-atualizador", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 - endereço fixo do site do JARVIS
        return r.read(MAX_FILE + 1)


def _get_curl(url: str) -> bytes:
    """O curl.exe vem no Windows 10/11 e usa a conexão segura do Windows (a mesma do navegador)."""
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise OSError("curl indisponível")
    # --ssl-no-revoke: no Windows, com antivírus olhando a conexão, a checagem de revogação falha (erro 35)
    extra = ["--ssl-no-revoke"] if os.name == "nt" else []
    r = subprocess.run([curl, "-fsSL", *extra, "--max-time", str(TIMEOUT * 2), "-H", "Cache-Control: no-cache", url],  # noqa: S603
                       capture_output=True, check=False, timeout=TIMEOUT * 3, stdin=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise OSError(f"curl saiu com {r.returncode}: {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return r.stdout


_USE_CURL = {"on": False}


def _get(url: str) -> bytes:
    """Python primeiro; se a conexão dele falhar uma vez, segue pelo curl.exe do Windows."""
    if not _USE_CURL["on"]:
        try:
            return _get_python(url)
        except Exception:  # noqa: BLE001 - erro de conexão/SSL: tenta pelo Windows
            _USE_CURL["on"] = True
    return _get_curl(url)


def local_commit(root: Path) -> str:
    """Commit atual do git deste PC ("" se não der)."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, check=False, timeout=15,  # noqa: S603,S607
                           stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout.decode().strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def same_code(manifest: dict, local_hash: str, commit: str) -> bool:
    """O site montou ESTE código? Pela impressão digital, ou pelo mesmo commit do git."""
    if manifest.get("source_hash") == local_hash:
        return True
    site_commit = str(manifest.get("commit") or "")
    return bool(commit) and len(site_commit) >= 7 and site_commit == commit


def fetch(frontend: Path, base_url: str = BASE_URL, get=_get, log=print, wait_s: float = 0, sleep=time.sleep,
          commit: str | None = None) -> bool:
    """wait_s: logo depois de uma versão nova o site leva 1 a 3 min para ficar pronto; espera até esse tempo."""
    frontend = Path(frontend)
    local = source_hash(frontend)
    if commit is None:
        commit = local_commit(frontend.parent)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            manifest = json.loads(get(base_url.rstrip("/") + "/files.json?t=" + str(int(time.time()))).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            log(f"  Interface pronta indisponível ({exc}).")
            return False
        if same_code(manifest, local, commit):
            break
        if time.monotonic() >= deadline:
            log(f"  A interface pronta do site ainda é de outra versão (site {manifest.get('versao', '?')} "
                f"{str(manifest.get('commit') or '')[:7]}, PC {commit[:7]}): montando aqui mesmo.")
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
    # V8.3.2: instala ARQUIVO POR ARQUIVO dentro da dist (antes renomeava a pasta inteira, e numa pasta do OneDrive
    # isso dava "Acesso negado" no último passo). Os arquivos de /assets/ têm nomes novos a cada versão; o
    # index.html (que aponta para eles) é trocado POR ÚLTIMO, então a página nunca fica pela metade.
    try:
        _install(tmp, dist, [str(i["p"]) for i in files])
    except Exception as exc:  # noqa: BLE001
        log(f"  Não consegui instalar a interface pronta ({exc}): montando aqui mesmo.")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    now = time.time()
    os.utime(dist / "index.html", (now, now))  # mais nova que o código: o --stale vê que está em dia
    log(f"  Interface pronta baixada ({len(files)} arquivos, versão {manifest.get('versao', '?')}).")
    return True


def _replace(src: Path, dst: Path, tries: int = 8, sleep=time.sleep) -> None:
    """Troca um arquivo resistindo ao OneDrive/antivírus segurando o antigo por um instante."""
    for attempt in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == tries - 1:
                shutil.copyfile(src, dst)  # último recurso: escreve por cima
                return
            sleep(0.2 * (attempt + 1))


def _install(new: Path, dist: Path, rels: list[str]) -> None:
    """Põe os arquivos de `new` dentro de `dist`: primeiro tudo menos o index.html, depois o index.html; no fim
    apaga (se der) os arquivos de /assets/ que a versão nova não usa mais."""
    dist.mkdir(parents=True, exist_ok=True)
    for rel in sorted(rels, key=lambda r: r == "index.html"):
        dst = dist / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        _replace(new / rel, dst)
    keep = {(dist / r).resolve() for r in rels}
    assets = dist / "assets"
    if assets.is_dir():
        for f in assets.rglob("*"):
            if f.is_file() and f.resolve() not in keep:
                try:
                    f.unlink()
                except OSError:
                    pass  # preso: fica de sobra, não atrapalha


def _log_to_file(root: Path):
    """Mostra na tela E guarda em logs/prebuilt.log."""
    path = root / "logs" / "prebuilt.log"

    def write(msg: str) -> None:
        print(msg)
        try:
            path.parent.mkdir(exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%d/%m %H:%M:%S')} {msg.strip()}\n")
        except OSError:
            pass
    return write


if __name__ == "__main__":
    fe = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "frontend"
    out = _log_to_file(fe.resolve().parent)
    sys.exit(0 if fetch(fe, log=out, wait_s=float(os.getenv("JARVIS_PREBUILT_WAIT", "60"))) else 1)
