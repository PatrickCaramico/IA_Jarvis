"""V9.5.3: baixa a versão mais nova ANTES de ligar (Iniciar-JARVIS.bat atualizar / botão ⟳ ATUALIZAR E LIGAR).

Com o JARVIS do PC fora do ar, a central do site não tinha como atualizar (quem atualiza é o próprio JARVIS). Agora o
botão da tela "Reconectando" chama o atalho jarvis://atualizar, e o Iniciar roda este script antes de subir: usa o
mesmo "git pull seguro" do botão ATUALIZAR (backend/modules/self_update.py: nunca apaga mudanças locais). Funciona
mesmo se a versão atual não liga, porque só importa o self_update. Registro em logs/ligar.log.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

log = logging.getLogger("jarvis.atualizar")


def update() -> dict:
    """Roda o git pull seguro. Nunca levanta exceção: devolve {ok, changed, message}."""
    try:
        from modules import self_update

        return self_update.pull()
    except Exception as exc:  # noqa: BLE001 - qualquer problema vira mensagem; o Iniciar liga mesmo assim
        log.exception("Não consegui atualizar antes de ligar")
        return {"ok": False, "changed": False, "message": f"Não consegui atualizar: {exc}"}


def main() -> int:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / "logs" / "ligar.log", level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(message)s")
    res = update()
    log.info("Atualizar antes de ligar: %s", res.get("message", ""))
    print(f"  {res.get('message', '')}")
    return 0  # o Iniciar continua e liga com o que tiver


if __name__ == "__main__":
    sys.exit(main())
