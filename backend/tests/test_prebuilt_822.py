"""V8.2.2: interface pronta baixada do site (sem montar no PC), com a mesma impressão digital do Netlify."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prebuilt", ROOT / "scripts" / "prebuilt.py")
prebuilt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prebuilt)


def _fixture(tmp_path, crlf=False):
    fe = tmp_path / "frontend"
    (fe / "src" / "sub").mkdir(parents=True)
    nl = "\r\n" if crlf else "\n"
    (fe / "src" / "a.js").write_bytes(f"export const a = 1;{nl}".encode())
    (fe / "src" / "sub" / "b.jsx").write_bytes(f"ç{nl}x{nl}".encode())
    (fe / "src" / ".DS_Store").write_bytes(b"lixo")
    (fe / "index.html").write_text("<html></html>")
    (fe / "package.json").write_text("{}")
    return fe


def test_hash_same_in_python_and_node_and_ignores_crlf(tmp_path):
    fe = _fixture(tmp_path)
    py = prebuilt.source_hash(fe)
    # V8.11: URL file:// (no Windows o Node recusa import('D:/...'): "protocolo d:" — o CI do Windows quebrava)
    node = subprocess.run(["node", "-e", f"import('{(ROOT / 'scripts/netlify/manifest.mjs').as_uri()}').then(m => console.log(m.sourceHash({json.dumps(str(fe))})))"],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert py == node
    assert prebuilt.source_hash(_fixture(tmp_path / "w", crlf=True)) == py  # Windows (CRLF) = Netlify (LF)


def test_fetch_installs_only_when_versions_match(tmp_path):
    fe = _fixture(tmp_path)
    (fe / "dist").mkdir()
    (fe / "dist" / "index.html").write_text("velho")
    files = {"index.html": b"<html>novo</html>", "assets/app-1.js": b"console.log(1)"}
    man = {"versao": "8.2.2", "source_hash": prebuilt.source_hash(fe),
           "arquivos": [{"p": p, "sha256": hashlib.sha256(d).hexdigest()} for p, d in files.items()]}
    site = {"files.json": json.dumps(man).encode(), **files}

    def get(url):
        return site[url.split("/pc/", 1)[1].split("?")[0]]

    msgs = []
    assert prebuilt.fetch(fe, "https://x/pc/", get=get, log=msgs.append) is True
    assert (fe / "dist" / "index.html").read_bytes() == b"<html>novo</html>"
    assert (fe / "dist" / "assets" / "app-1.js").exists() and not (fe / "dist.novo").exists()
    # arquivo adulterado: não troca nada
    site["assets/app-1.js"] = b"malicioso"
    (fe / "dist" / "index.html").write_text("atual")
    assert prebuilt.fetch(fe, "https://x/pc/", get=get, log=msgs.append) is False
    assert (fe / "dist" / "index.html").read_text() == "atual"
    # site ainda em outra versão: não baixa
    man["source_hash"] = "outra"
    site["files.json"] = json.dumps(man).encode()
    assert prebuilt.fetch(fe, "https://x/pc/", get=get, log=msgs.append) is False
    # caminho que tenta sair da pasta: recusado
    man["source_hash"] = prebuilt.source_hash(fe)
    man["arquivos"] = [{"p": "../fora.txt", "sha256": "x"}]
    site["files.json"] = json.dumps(man).encode()
    assert prebuilt.fetch(fe, "https://x/pc/", get=get, log=msgs.append) is False
    assert not (fe / "fora.txt").exists()


def test_bat_tries_prebuilt_before_npm():
    bat = (ROOT / "Iniciar-JARVIS.bat").read_text(encoding="utf-8", errors="replace")
    assert bat.index("prebuilt.py") < bat.index("npm run build")
    assert "_site/pc" in (ROOT / "scripts/netlify/montar_site.sh").read_text()


def test_fetch_waits_for_site_to_finish(tmp_path):
    fe = _fixture(tmp_path)
    good = prebuilt.source_hash(fe)
    data = b"<html>ok</html>"
    calls = {"n": 0}

    def get(url):
        if "files.json" in url:
            calls["n"] += 1
            h = good if calls["n"] >= 3 else "antiga"
            return json.dumps({"versao": "x", "source_hash": h, "arquivos": [{"p": "index.html", "sha256": hashlib.sha256(data).hexdigest()}]}).encode()
        return data

    slept = []
    assert prebuilt.fetch(fe, "https://x/pc/", get=get, log=lambda m: None, wait_s=3600, sleep=slept.append) is True
    assert calls["n"] == 3 and slept == [15, 15]


def test_v823_bat_starts_jarvis_before_building():
    """V8.2.3: com interface já montada, o .bat liga o JARVIS na hora e monta a nova em segundo plano."""
    bat = (ROOT / "Iniciar-JARVIS.bat").read_text(encoding="utf-8", errors="replace")
    assert "BUILD_LATER" in bat
    start_backend = bat.index("run_server.py")
    bg = bat.index("if defined BUILD_LATER")
    assert start_backend < bg  # o build em segundo plano vem depois de ligar o backend
    assert "JARVIS_PREBUILT_WAIT=20" in bat


def test_v823_background_build_lock_and_log(tmp_path, monkeypatch):
    spec2 = importlib.util.spec_from_file_location("bg", ROOT / "scripts" / "build_background.py")
    bg = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(bg)
    monkeypatch.setattr(bg, "LOGS", tmp_path)
    monkeypatch.setattr(bg, "LOCK", tmp_path / "build.running")
    monkeypatch.setattr(bg, "FRONTEND", tmp_path)
    import shutil as _sh
    import sys

    (tmp_path / "build.running").write_text("1")
    assert bg.main() == 0  # já tem uma rodando: não começa outra
    (tmp_path / "build.running").unlink()
    monkeypatch.setattr(_sh, "which", lambda n: sys.executable)
    monkeypatch.setattr(bg, "try_prebuilt", lambda out, wait_s=0: False)  # V8.3.1: site sem a versão: monta no PC
    monkeypatch.setattr(bg.subprocess, "call", lambda cmd, **kw: (kw["stdout"].write("built\n"), 0)[1])
    assert bg.main() == 0
    log = (tmp_path / "build.log").read_text(encoding="utf-8")  # V8.11: no Windows o padrão é cp1252 ("código")
    assert "built" in log and "Fim: código 0" in log and not (tmp_path / "build.running").exists()
    bat = (ROOT / "Iniciar-JARVIS.bat").read_text(encoding="utf-8", errors="replace")
    assert "build_background.py" in bat and "'/c npm run build" not in bat


def test_v831_background_prefers_site_and_never_runs_npm_when_it_works(tmp_path, monkeypatch):
    spec2 = importlib.util.spec_from_file_location("bg2", ROOT / "scripts" / "build_background.py")
    bg = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(bg)
    monkeypatch.setattr(bg, "LOGS", tmp_path)
    monkeypatch.setattr(bg, "LOCK", tmp_path / "build.running")
    import shutil as _sh
    import sys

    monkeypatch.setattr(_sh, "which", lambda n: sys.executable)
    monkeypatch.setattr(bg, "try_prebuilt", lambda out, wait_s=0: True)
    monkeypatch.setattr(bg.subprocess, "call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não devia montar")))
    assert bg.main() == 0
    assert "interface pronta do site instalada" in (tmp_path / "build.log").read_text(encoding="utf-8")
    assert bg.PREBUILT_WAIT >= 300


def test_v831_same_commit_counts_and_curl_fallback(tmp_path, monkeypatch):
    pb = prebuilt
    assert pb.same_code({"source_hash": "x"}, "x", "")
    assert pb.same_code({"source_hash": "y", "commit": "abc1234def"}, "x", "abc1234def")
    assert not pb.same_code({"source_hash": "y", "commit": "abc1234def"}, "x", "fff")
    assert not pb.same_code({"source_hash": "y", "commit": ""}, "x", "")
    # o Python não consegue baixar (SSL cortado): segue pelo curl do Windows, e continua por ele
    calls = []
    monkeypatch.setattr(pb, "_get_python", lambda u: (_ for _ in ()).throw(OSError("SSL EOF")))
    monkeypatch.setattr(pb, "_get_curl", lambda u: calls.append(u) or b"ok")
    pb._USE_CURL["on"] = False
    assert pb._get("https://x/a") == b"ok" and pb._get("https://x/b") == b"ok"
    assert calls == ["https://x/a", "https://x/b"]
    pb._USE_CURL["on"] = False
    # mesmo commit do site: instala mesmo com um arquivo do PC diferente (ex.: package-lock mexido)
    fe = tmp_path / "frontend"
    (fe / "src").mkdir(parents=True)
    (fe / "src" / "a.js").write_text("1")
    (fe / "dist").mkdir()
    page = b"<html>novo</html>"
    man = {"versao": "8.3.1", "commit": "c0ffee1234", "source_hash": "outro",
           "arquivos": [{"p": "index.html", "sha256": hashlib.sha256(page).hexdigest()}]}
    files = {"files.json": json.dumps(man).encode(), "index.html": page}
    get = lambda url: files[url.split("/pc/")[-1].split("?")[0]]  # noqa: E731
    assert pb.fetch(fe, base_url="https://site/pc/", get=get, log=lambda m: None, commit="c0ffee1234")
    assert (fe / "dist" / "index.html").read_bytes() == page
    assert not pb.fetch(fe, base_url="https://site/pc/", get=get, log=lambda m: None, commit="0000000")
    mjs = (ROOT / "scripts" / "netlify" / "manifest.mjs").read_text(encoding="utf-8")
    assert "COMMIT_REF" in mjs


def test_v832_installs_file_by_file_without_renaming_dist(tmp_path, monkeypatch):
    """No OneDrive, renomear a pasta dist dava "Acesso negado": agora troca arquivo por arquivo, index por último."""
    dist, new = tmp_path / "dist", tmp_path / "novo"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("velho")
    (dist / "assets" / "index-OLD.js").write_text("old")
    (new / "assets").mkdir(parents=True)
    (new / "index.html").write_text("novo")
    (new / "assets" / "index-NEW.js").write_text("new")
    order = []
    real = prebuilt.os.replace
    monkeypatch.setattr(prebuilt.os, "replace", lambda a, b: (order.append(Path(b).name), real(a, b)))
    monkeypatch.setattr(Path, "rename", lambda *a: (_ for _ in ()).throw(AssertionError("não pode renomear a pasta")))
    prebuilt._install(new, dist, ["assets/index-NEW.js", "index.html"])
    assert order == ["index-NEW.js", "index.html"]
    assert (dist / "index.html").read_text() == "novo" and (dist / "assets" / "index-NEW.js").exists()
    assert not (dist / "assets" / "index-OLD.js").exists()


def test_v832_replace_survives_locked_file(tmp_path, monkeypatch):
    src, dst = tmp_path / "a", tmp_path / "b"
    src.write_text("novo")
    dst.write_text("velho")
    monkeypatch.setattr(prebuilt.os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError(5, "Acesso negado")))
    prebuilt._replace(src, dst, tries=3, sleep=lambda s: None)
    assert dst.read_text() == "novo"
