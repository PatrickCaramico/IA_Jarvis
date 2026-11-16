"""V8.2.4: um ")" sem ^ num echo dentro de um bloco ( ... ) fecha o bloco antes da hora e o cmd para com
"... foi inesperado neste momento" (o Iniciar-JARVIS.bat parava antes de ligar o JARVIS desde a 8.1.5)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATS = sorted(p for p in ROOT.rglob("*.bat") if "node_modules" not in p.parts and "venv" not in p.parts)


def problems(text: str) -> list[str]:
    out, depth = [], 0
    for n, line in enumerate(text.replace("\r", "").split("\n"), 1):
        s = line.strip()
        low = s.lower()
        if low == "rem" or low.startswith("rem ") or s.startswith("::"):
            continue
        t = re.sub(r'"[^"]*"', "", s).replace("^(", "").replace("^)", "")
        if low.startswith("echo"):
            if depth > 0 and ")" in t:
                out.append(f"linha {n}: {s}")
            continue
        depth += t.count("(") - t.count(")")
    if depth:
        out.append(f"parenteses desbalanceados ({depth})")
    return out


def test_checker_finds_the_bug():
    assert problems('if errorlevel 1 (\r\n  echo  Atualizando (edge-tts)...\r\n)\r\n')
    assert not problems('if errorlevel 1 (\r\n  echo  Atualizando ^(edge-tts^)...\r\n)\r\n')


def test_all_bats_parse():
    assert BATS
    for bat in BATS:
        assert problems(bat.read_text(encoding="latin-1")) == [], bat.name


def test_bats_use_crlf():
    for bat in BATS:
        data = bat.read_bytes()
        assert data.count(b"\n") == data.count(b"\r\n"), bat.name
