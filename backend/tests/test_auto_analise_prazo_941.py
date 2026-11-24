"""V9.4.1: a auto-análise não estoura mais o tempo com a memória alta: cada etapa tem prazo e a resposta sai com o resto."""
import asyncio
import time

from core.skills import router
from skills import auto_analise as aa


def test_slow_process_list_does_not_kill_the_analysis(real_skills, monkeypatch):
    monkeypatch.setitem(aa.STEP_LIMIT_S, "processos", 0.3)

    def slow_processes():
        time.sleep(2)  # o Windows sobrecarregado demorando para listar os programas
        return []

    def slow_tabs_probe():
        time.sleep(0.25)  # como no Windows: o navegador do JARVIS fechado demora a recusar a conexão
        return False

    monkeypatch.setattr("skills.system_guard.processes", slow_processes)
    monkeypatch.setattr("skills.navegador.cdp.available", slow_tabs_probe)
    t0 = time.monotonic()
    snap = aa.snapshot()
    # V9.4.2: as etapas rodam juntas: o total é o prazo da mais lenta (0,3 s), não a soma
    assert time.monotonic() - t0 < 1.5 and snap["slow"] == ["processos"] and snap["procs"] == []
    result = aa.diagnose({**snap, "ram": 91, "cpu": 40})
    assert "demorou para listar os programas" in result["speech"]
    assert any(f["label"] == "Programas" for f in result["findings"])


def test_skill_answers_instead_of_timeout(real_skills, monkeypatch):
    monkeypatch.setattr(aa, "snapshot", lambda: {"cpu": 30, "ram": 92, "ram_total_gb": 16, "procs": [], "slow": ["processos"],
                                                  "jarvis_mb": 300, "uptime_days": 1, "tabs": None})
    res = asyncio.run(router.try_fast_path("faz uma auto análise"))
    assert res.ok and res.speech.startswith("Memória em 92%") and "demorou para listar" in res.speech
