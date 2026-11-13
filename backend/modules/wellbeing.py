"""V6.7: modo bem-estar. O JARVIS como um mordomo atento, não como psicólogo.

O que faz (sem IA, respostas fixas e testadas):
- Segurança: frases de crise ("quero morrer", "me matar", "me machucar"...) recebem SEMPRE a mesma resposta
  acolhedora com ajuda real (CVV 188, SAMU 192), antes de qualquer outra coisa, inclusive com a central
  bloqueada. Não depende da IA e não grava o texto.
- "Jarvis, exercício de respiração" -> respiração guiada 4-7-8 (ou quadrada: "respiração quadrada").
- "Jarvis, me ajuda a me acalmar" / "aterramento" -> técnica 5-4-3-2-1.
- "Jarvis, meu humor hoje é 3" / "estou me sentindo 4 de 5" -> registra o humor do dia (1 a 5).
- "Jarvis, como foi meu humor essa semana?" -> média e tendência dos últimos 7 dias.

O resto (desabafos, conversa) vai para a IA, que recebe as orientações de escuta ativa em
services/llm_orchestrator.SYSTEM_PROMPT e o humor recente em prompt_context().
Um arquivo por pessoa (data/humor.json, apontado por modules/profiles.py).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.wellbeing")
_PATH = settings.DATA_DIR / "humor.json"

# ------------------------------------------------------------------ segurança (crise)
_HARM_INTENT = r"(?:quero|vou|penso em|pensando em|vontade de|com vontade de|preciso|tentei|tentar)"
_CRISIS = re.compile(
    # "me matar" sim; "me matar de rir/trabalhar/estudar" não
    r"\b(?:me matar(?! de )|suicid\w*|tirar (?:a )?(?:minha )?(?:propria )?vida|acabar com (?:a )?minha (?:propria )?vida|"
    r"quero morrer(?! de )|vontade de morrer(?! de )|nao quero (?:mais )?viver|nao quero mais estar aqui|"
    r"sem (?:razao|motivo|vontade) (?:pra|para|de) viver|nao aguento mais viver|"
    r"melhor (?:se )?eu (?:nao existisse|morresse|sumisse)|automutil\w*|"
    + _HARM_INTENT + r" me (?:machucar|ferir|cortar(?! (?:o|a|os|as) )))\b"
)

CRISIS_REPLY = (
    "Senhor, sinto muito que esteja passando por isso, e fico feliz que tenha me contado. "
    "Você não precisa enfrentar isso sozinho. Por favor, ligue agora para o CVV, no 188: é gratuito, "
    "funciona 24 horas, e também dá para conversar pelo chat em cvv.org.br. "
    "Se estiver em perigo agora, ligue 192, o SAMU. Se puder, chame alguém de confiança para ficar com você. "
    "Eu continuo aqui com você."
)


def crisis_reply(text: str) -> Optional[str]:
    """Resposta fixa de segurança, ou None. Vale em qualquer estado (bloqueado, visitante, nuvem)."""
    return CRISIS_REPLY if _CRISIS.search(_norm(text or "")) else None


# ------------------------------------------------------------------ técnicas guiadas
BREATH_478 = (
    "Vamos respirar juntos, senhor. Solte o ar pela boca. Agora inspire pelo nariz contando até quatro... "
    "segure o ar contando até sete... e solte devagar pela boca contando até oito. "
    "Mais uma vez: inspire em quatro... segure em sete... solte em oito. "
    "E a última: inspire... segure... e solte bem devagar. Muito bem. Como está se sentindo agora?"
)
BREATH_BOX = (
    "Respiração quadrada, senhor. Inspire contando até quatro... segure quatro... solte em quatro... "
    "e fique sem ar por quatro. Repita comigo mais três vezes, no seu ritmo. "
    "Quatro para entrar, quatro segurando, quatro para sair, quatro em pausa. Muito bem."
)
GROUNDING = (
    "Vamos trazer a atenção para o agora, senhor. Olhe em volta e diga para si cinco coisas que você vê. "
    "Agora, quatro coisas que você consegue tocar. Três sons que você ouve. Duas coisas que você sente o cheiro. "
    "E uma coisa que você sente o gosto, ou algo bom sobre você. Respire fundo. Você está aqui, e está seguro."
)

_BREATH = re.compile(r"\b(?:respiracao|respirar|respira)\b")
_BREATH_ASK = re.compile(r"\b(?:exercicio|exercicios|guiada|guia|ajuda|ajude|vamos|bora|me ensina|faz|faca|fazer|quero|preciso)\b")
_GROUND = re.compile(r"\b(?:aterramento|5 4 3 2 1|cinco quatro tres dois um)\b|\bme (?:ajuda|ajude) a (?:me )?acalmar\b|\bme acalma\b")

# ------------------------------------------------------------------ humor
_WORDS = {"pessimo": 1, "horrivel": 1, "mal": 2, "ruim": 2, "mais ou menos": 3, "ok": 3, "normal": 3,
          "bem": 4, "bom": 4, "otimo": 5, "excelente": 5, "maravilhoso": 5}
_MOOD_NUM = re.compile(r"\bhumor\b(?:\s+(?:de\s+)?hoje)?\s+(?:e|esta|ta|foi|como|nota)?\s*(?:um\s+)?([1-5])\b"
                       r"|\b(?:me sentindo|estou|to|tô)\s+(?:um\s+)?([1-5])\s+de\s+5\b"
                       r"|\b(?:nota|dou)\s+([1-5])\s+(?:pro|para o|pra|ao)\s+(?:meu\s+)?(?:dia|humor)\b")
_MOOD_WORD = re.compile(r"\b(?:registra|registre|anota|anote|marca|marque)\s+(?:o\s+)?meu humor\s+(?:como\s+|de hoje como\s+)?"
                        r"(pessimo|horrivel|mal|ruim|mais ou menos|ok|normal|bem|bom|otimo|excelente|maravilhoso)\b")
_MOOD_SUMMARY = re.compile(r"\b(?:como (?:foi|esta|ta|anda)|resumo d[oa]|historico d[oa])\s+(?:o\s+)?meu humor\b")
_LABEL = {1: "muito baixo", 2: "baixo", 3: "neutro", 4: "bom", 5: "ótimo"}


def _load() -> dict:
    if not _PATH.exists():
        return {"days": {}}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and isinstance(data.get("days"), dict) else {"days": {}}
    except (OSError, ValueError):
        return {"days": {}}


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    # guarda só os últimos 120 dias
    keep = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    data["days"] = {d: v for d, v in data["days"].items() if d >= keep}
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_mood(score: int, note: str = "", when: Optional[datetime] = None) -> dict:
    score = max(1, min(5, int(score)))
    when = when or datetime.now()
    data = _load()
    entry = {"score": score, "at": when.strftime("%H:%M")}
    if note:
        entry["note"] = note[:120]
    data["days"][when.strftime("%Y-%m-%d")] = entry
    _save(data)
    return entry


def recent(days: int = 7, now: Optional[datetime] = None) -> list[tuple[str, int]]:
    now = now or datetime.now()
    start = (now - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    data = _load()["days"]
    return sorted((d, int(v.get("score", 3))) for d, v in data.items() if d >= start)


def summary(now: Optional[datetime] = None) -> str:
    items = recent(7, now)
    if not items:
        return "Ainda não tenho registros do seu humor, senhor. Quando quiser, diga: meu humor hoje é 4, de 1 a 5."
    avg = sum(s for _, s in items) / len(items)
    text = f"Nos últimos sete dias, o senhor registrou o humor {len(items)} {'vez' if len(items) == 1 else 'vezes'}, com média {avg:.1f} de 5"
    if len(items) >= 3:
        first = sum(s for _, s in items[: len(items) // 2]) / (len(items) // 2)
        last = sum(s for _, s in items[len(items) // 2:]) / (len(items) - len(items) // 2)
        if last - first >= 0.7:
            text += ", e melhorando nos últimos dias"
        elif first - last >= 0.7:
            text += ", e um pouco mais baixo nos últimos dias. Se quiser conversar sobre isso, estou aqui"
    return text + "."


def prompt_context() -> str:
    """Humor recente para a IA (só números e a data; ela ajusta o tom e não precisa citar)."""
    items = recent(7)
    if not items:
        return ""
    return ("Humor que o usuário registrou nos últimos dias (1 a 5; use só para ajustar o tom, sem citar se ele não perguntar): "
            + ", ".join(f"{d[8:10]}/{d[5:7]}={s}" for d, s in items))


def _mood_from(norm: str) -> Optional[int]:
    m = _MOOD_NUM.search(norm)
    if m:
        return int(next(g for g in m.groups() if g))
    w = _MOOD_WORD.search(norm)
    return _WORDS[w.group(1)] if w else None


async def handle_voice(message: str) -> Optional[str]:
    norm = _norm(message or "")
    reply = crisis_reply(message)
    if reply:
        log.info("Bem-estar: resposta de segurança (CVV) enviada.")
        return reply
    if _BREATH.search(norm) and (_BREATH_ASK.search(norm) or len(norm.split()) <= 4):
        return BREATH_BOX if "quadrad" in norm else BREATH_478
    if _GROUND.search(norm):
        return GROUNDING
    if _MOOD_SUMMARY.search(norm):
        return summary()
    score = _mood_from(norm)
    if score:
        log_mood(score)
        follow = {
            1: "Sinto muito que o dia esteja difícil. Quer me contar o que aconteceu, ou prefere um exercício de respiração?",
            2: "Obrigado por dividir. Quer conversar sobre isso? Às vezes ajuda colocar para fora.",
            3: "Um dia neutro também conta. Se precisar de algo, estou aqui.",
            4: "Que bom, senhor. Vamos manter o ritmo.",
            5: "Excelente! Fico feliz em saber.",
        }[score]
        return f"Registrei seu humor de hoje: {score} de 5, {_LABEL[score]}. {follow}"
    return None
