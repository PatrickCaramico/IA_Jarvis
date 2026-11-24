"""V9.4.1: o ATUALIZAR não trava mais com a pasta "fora do lugar" e a atualização automática avisa e atualiza sozinha.

Os casos do pull rodam com repositórios Git de verdade numa pasta temporária (um "GitHub" local e um "PC")."""
import asyncio
import shutil
import subprocess

import pytest

from core import runtime, speech
from modules import auto_update, self_update

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="precisa do git")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repos(tmp_path, monkeypatch):
    """remote = o GitHub; pc = a pasta do JARVIS no PC (clonada do main)."""
    remote, seed, pc = tmp_path / "remote.git", tmp_path / "seed", tmp_path / "pc"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    for d in (seed,):
        git(d, "config", "user.email", "t@t")
        git(d, "config", "user.name", "t")
    (seed / "frontend").mkdir()
    (seed / "frontend" / "package-lock.json").write_text("{}\n")
    (seed / "app.txt").write_text("v1\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "v1")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", str(remote), str(pc)], check=True)
    git(pc, "config", "user.email", "t@t")
    git(pc, "config", "user.name", "t")
    monkeypatch.setattr(self_update, "ROOT", pc)

    def publish(text="v2\n"):
        (seed / "app.txt").write_text(text)
        git(seed, "commit", "-qam", f"nova {text.strip()}")
        git(seed, "push", "-q", "origin", "main")

    return {"remote": remote, "seed": seed, "pc": pc, "publish": publish}


def test_simple_update(repos):
    repos["publish"]()
    r = self_update.pull()
    assert r["ok"] and r["changed"] and (repos["pc"] / "app.txt").read_text() == "v2\n"
    again = self_update.pull()
    assert again["ok"] and not again["changed"] and again["message"] == "Já estava na versão mais nova."


def test_regenerated_package_lock_does_not_block(repos):
    (repos["pc"] / "frontend" / "package-lock.json").write_text('{"mexido pelo npm install": true}\n')
    repos["publish"]()
    r = self_update.pull()
    assert r["ok"] and r["changed"] and not r["stashed"]
    assert (repos["pc"] / "frontend" / "package-lock.json").read_text() == "{}\n"


def test_other_local_changes_are_kept_in_a_stash(repos):
    (repos["pc"] / "app.txt").write_text("mexi aqui\n")
    repos["publish"]()
    r = self_update.pull()
    assert r["ok"] and r["changed"] and r["stashed"] and "git stash" in r["message"]
    assert (repos["pc"] / "app.txt").read_text() == "v2\n"
    assert "mudanças locais guardadas" in git(repos["pc"], "stash", "list")  # nada se perdeu


def test_branch_deleted_on_github_goes_back_to_main(repos):
    pc = repos["pc"]
    git(pc, "checkout", "-qb", "claude/antigo")
    git(pc, "push", "-q", "-u", "origin", "claude/antigo")
    git(repos["seed"], "push", "-q", "origin", "--delete", "claude/antigo")  # o ramo foi apagado depois do merge
    repos["publish"]()
    r = self_update.pull()
    assert r["ok"] and r["switched"] == "main" and git(pc, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert (pc / "app.txt").read_text() == "v2\n"
    info = self_update.check(force=True)
    assert info["available"] is False


def test_local_commits_are_never_lost(repos):
    pc = repos["pc"]
    (pc / "meu.txt").write_text("meu\n")
    git(pc, "add", "meu.txt")
    git(pc, "commit", "-qm", "commit local")
    repos["publish"]()
    r = self_update.pull()
    assert not r["ok"] and "commits" in r["message"] and (pc / "meu.txt").exists()


# ------------------------------------------------------------------ atualização automática
@pytest.fixture
def auto(monkeypatch):
    sent, notes, said, updates = [], [], [], []

    async def fake_broadcast(e):
        sent.append(e)

    async def fake_say(text):
        said.append(text)

    async def fake_update(announce=True):
        updates.append(announce)
        return {"status": "restarting", "boot_id": "b1", "before": "a", "after": "b", "changed": True, "versao_nova": "9.9.9"}

    async def no_sleep(s):
        return None

    import routes.system as rs

    monkeypatch.setattr(runtime.manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(runtime, "notify", lambda kind, title, body: notes.append(body))
    monkeypatch.setattr(speech, "say_quietly", fake_say)
    monkeypatch.setattr(rs, "perform_update", fake_update)
    monkeypatch.setattr(auto_update, "enabled", lambda: True)
    monkeypatch.setattr(auto_update, "is_quiet", lambda now=None: True)
    monkeypatch.setattr(self_update, "check", lambda force=False: {"available": True, "latest": "9.9.9", "notes": ["JARVIS 9.9.9"]})
    return {"sent": sent, "notes": notes, "said": said, "updates": updates, "sleep": no_sleep}


def test_warns_then_updates_by_itself(auto):
    assert asyncio.run(auto_update.check_and_update(sleep=auto["sleep"])) == "atualizando"
    soon = next(e for e in auto["sent"] if e["type"] == "update_soon")
    assert soon["version"] == "9.9.9" and soon["in_s"] == auto_update.NOTICE_S
    assert "9.9.9" in auto["notes"][0] and auto["said"] and "dois minutos" in auto["said"][0]
    assert auto["updates"] == [False]
    assert auto["sent"][-1]["type"] == "update_started" and auto["sent"][-1]["boot_id"] == "b1"


def test_postpone_and_update_now(auto, monkeypatch):
    auto_update.postpone(now=1000.0, seconds=3600)
    assert asyncio.run(auto_update.check_and_update(sleep=auto["sleep"], now=lambda: 1500.0)) == "adiada"
    assert auto["updates"] == [] and not auto["sent"]
    assert auto_update.postponed(now=1500.0) and not auto_update.postponed(now=5000.0)

    # adiou no meio do aviso: cancela a rodada
    auto_update.reset_for_tests()

    async def postpone_during(s):
        auto_update.postpone()

    assert asyncio.run(auto_update.check_and_update(sleep=postpone_during)) == "adiada"
    assert auto["sent"][-1] == {"type": "update_soon", "cancelled": True} and auto["updates"] == []

    # ATUALIZAR AGORA: não espera os 2 minutos nem o "parado"
    auto_update.reset_for_tests()
    monkeypatch.setattr(auto_update, "is_quiet", lambda now=None: False)
    slept = []

    async def count_sleep(s):
        slept.append(s)
        auto_update.update_now()

    assert asyncio.run(auto_update.check_and_update(sleep=count_sleep)) == "atualizando" and len(slept) == 1


def test_failure_is_reported_once(auto, monkeypatch):
    import routes.system as rs

    async def broken(announce=True):
        return {"status": "error", "message": "Esta pasta tem alterações próprias (commits)."}

    monkeypatch.setattr(rs, "perform_update", broken)
    assert asyncio.run(auto_update.check_and_update(sleep=auto["sleep"])) == "erro"
    assert auto["sent"][-1]["cancelled"] and "commits" in auto["sent"][-1]["error"]
    count = len(auto["said"])
    assert asyncio.run(auto_update.check_and_update(sleep=auto["sleep"])) == "erro"
    assert len(auto["said"]) == count  # não repete o aviso a cada 40 min


def test_schedule_and_routes():
    from fastapi.testclient import TestClient

    import main

    assert auto_update.CHECK_EVERY_S == 40 * 60 and auto_update.FIRST_CHECK_S <= 5 * 60
    with TestClient(main.app) as client:
        assert client.post("/api/system/update/postpone").json()["postponed_until"] > 0
        assert auto_update.postponed()
        assert client.post("/api/system/update/now").json() == {"status": "ok"}
        assert not auto_update.postponed()
