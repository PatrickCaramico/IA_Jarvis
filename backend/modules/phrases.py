"""V6.5.3: frases variadas para a entrada (desbloqueio, briefing, "em que posso ajudar?").

Toda sessão começava com as mesmas palavras ("Olá, boa tarde, Patrick. Tudo bem?", "Revisei o que já
está consolidado..."). Agora cada momento tem várias versões no tom do JARVIS (educado, curto, com
"senhor") e o sorteio evita repetir as últimas usadas — inclusive depois de reiniciar o PC.

Uso: phrases.pick("unlock_hello", tg="boa tarde", TG="Boa tarde", who=", Patrick")
"""
from __future__ import annotations

import json
import logging
import random

from config import settings

log = logging.getLogger("jarvis.phrases")

_PATH = settings.DATA_DIR / "frases_recentes.json"
AVOID_LAST = 2  # não repete nenhuma das 2 últimas de cada momento

# {tg} "boa tarde" · {TG} "Boa tarde" · {who} ", Patrick" (ou "") · {day} "quinta-feira, 12 de novembro"
# {period} "manhã" | "tarde" | "noite"
POOLS: dict[str, list[str]] = {
    # desbloqueio sem briefing pendente (rosto, digital)
    "unlock_hello": [
        "Olá, {tg}{who}. Tudo bem?",
        "{TG}{who}. Bom ter o senhor de volta.",
        "{TG}{who}. A central é toda sua.",
        "Olá{who}. {TG}! Tudo pronto por aqui.",
        "{TG}{who}. Sistemas no ar, aguardando suas ordens.",
        "{TG}{who}. Senti sua falta. Bom, na medida em que um programa sente.",
        "Bem-vindo{who}. {TG}, e tudo em ordem.",
        "{TG}{who}. O que vamos resolver agora?",
    ],
    # desbloqueio com o briefing logo em seguida (só confirma; quem cumprimenta é o briefing)
    "unlock_confirm": [
        "Identidade confirmada{who}.",
        "Reconhecido{who}.",
        "É o senhor mesmo{who}. Pode entrar.",
        "Acesso liberado{who}.",
        "Confirmado{who}. Preparando o seu resumo.",
    ],
    # entrada sem briefing e sem saudação extra (botão ENTRAR, /api/enter)
    "ready": [
        "Em que posso ajudar?",
        "Pronto, senhor. O que vai ser?",
        "Às ordens, senhor.",
        "Estou ouvindo, senhor.",
        "Tudo pronto. Por onde começamos?",
    ],
    # o briefing de hoje já foi: repetir ou pular?
    "ask_repeat": [
        "Quer que eu repita o briefing de hoje ou prefere pular?",
        "O resumo de hoje já foi. Repito ou seguimos?",
        "Já passamos o briefing de hoje. Quer ouvir de novo ou pular?",
        "Posso repetir o resumo do dia, se quiser. Repito ou pulo?",
    ],
    # abertura do briefing
    "briefing_morning": [
        "Bom dia{who}. Hoje é {day}.",
        "Bom dia{who}! {Day}, e aqui está o seu dia.",
        "Bom dia{who}. Vamos ao dia de hoje, {day}.",
        "Bom dia{who}. Café na mão? Hoje é {day}.",
        "Bom dia{who}. Já organizei o seu {day}.",
    ],
    "briefing_afternoon": [
        "Boa tarde{who}. Aqui está o resumo da tarde de {day}.",
        "Boa tarde{who}. Vamos ver como está a sua tarde.",
        "Boa tarde{who}. Metade do dia já foi; veja o que falta.",
        "Boa tarde{who}. Um panorama rápido da sua tarde.",
    ],
    "briefing_evening": [
        "Boa noite{who}. Aqui está o fechamento de {day}.",
        "Boa noite{who}. Vamos fechar o dia.",
        "Boa noite{who}. Hora do balanço de {day}.",
        "Boa noite{who}. Um resumo rápido antes de encerrar o dia.",
    ],
    # nada de anormal antes do briefing da manhã
    "no_deviations": [
        "Revisei o que já está consolidado e nada exige interromper a sua {period}.",
        "Nada fora do comum por enquanto.",
        "Tudo dentro do esperado até agora.",
        "Nenhum alerta pendente. Vamos ao resumo.",
        "Céu limpo nos sistemas. Vamos lá.",
    ],
}

_recent: dict[str, list[int]] | None = None


def _load() -> dict[str, list[int]]:
    global _recent
    if _recent is None:
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            _recent = {k: [int(i) for i in v][-AVOID_LAST:] for k, v in data.items() if isinstance(v, list)}
        except (OSError, ValueError, TypeError):
            _recent = {}
    return _recent


def _save() -> None:
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(json.dumps(_recent or {}), encoding="utf-8")
    except OSError as exc:
        log.debug("Não consegui guardar as frases recentes: %s", exc)


def choose_index(n: int, recent: list[int], rng: random.Random | None = None) -> int:
    """Sorteia um índice de 0 a n-1 fora dos recentes (se sobrar algum)."""
    rng = rng or random
    options = [i for i in range(n) if i not in recent[-AVOID_LAST:]] or list(range(n))
    return rng.choice(options)


class _Safe(dict):
    def __missing__(self, key):  # campo que não veio vira vazio (nunca quebra a fala)
        return ""


def pick(key: str, **fields) -> str:
    pool = POOLS[key]
    recent = _load().setdefault(key, [])
    i = choose_index(len(pool), recent)
    recent.append(i)
    del recent[:-AVOID_LAST]
    _save()
    day = fields.get("day", "")
    fields.setdefault("Day", day[:1].upper() + day[1:] if day else "")
    text = pool[i].format_map(_Safe(fields))
    return " ".join(text.split())
