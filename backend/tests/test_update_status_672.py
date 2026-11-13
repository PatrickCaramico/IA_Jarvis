"""V6.7.2: a central sabe quando há versão nova (bolinha com o número no botão ATUALIZAR)."""
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

import main
from modules import access, self_update

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def release(repo, version, subject):
    (repo / "backend").mkdir(exist_ok=True)
    (repo / "backend" / "version.py").write_text(f'VERSION = "{version}"\n', encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", subject)


@pytest.fixture
def repos(tmp_path, monkeypatch):
    origin, work = tmp_path / "origin", tmp_path / "work"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    release(origin, "6.7.1", "JARVIS 6.7.1: timers")
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    monkeypatch.setattr(self_update, "ROOT", work)
    self_update._last_check.update(at=0.0, result=None)
    return origin, work


def test_counts_new_versions(repos):
    origin, _ = repos
    r = self_update.check(force=True)
    assert r["available"] is False and r["count"] == 0 and r["current"] == "6.7.1"
    release(origin, "6.7.2", "JARVIS 6.7.2: bolinha de atualização")
    git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "Merge pull request #14")
    release(origin, "6.7.3", "JARVIS 6.7.3: outra coisa")
    r = self_update.check(force=True)
    assert r["available"] is True and r["count"] == 2 and r["latest"] == "6.7.3"
    assert r["notes"][0].startswith("JARVIS 6.7.3")
    # guarda o resultado por 15 min (não fica batendo no GitHub)
    release(origin, "6.7.4", "JARVIS 6.7.4: mais")
    assert self_update.check()["count"] == 2


def test_status_route_works_locked(repos, credentials):
    access.reset_for_tests(access.LOCKED)
    r = TestClient(main.app).get("/api/system/update/status")
    assert r.status_code == 200 and "available" in r.json()
