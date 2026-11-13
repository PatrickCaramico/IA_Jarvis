"""Memória local do JARVIS: fatos, preferências e contexto recente."""
import json
from datetime import datetime
from typing import Any, Optional

Optional_str = Optional[str]

from config import settings

_PATH = settings.DATA_DIR / "memoria.json"
_DEFAULTS = {"facts": [], "preferences": {}, "routine": [], "conversation": []}


def _fresh() -> dict[str, Any]:
    # V6.7.3: cópia nova a cada vez. Antes, _DEFAULTS.copy() (rasa) devolvia as MESMAS listas, e o primeiro
    # "lembre que..." sem arquivo de memória gravava dentro do próprio padrão.
    return json.loads(json.dumps(_DEFAULTS))


def _load() -> dict[str, Any]:
    if not _PATH.exists():
        return _fresh()
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return {**_fresh(), **data} if isinstance(data, dict) else _fresh()
    except (OSError, ValueError):
        return _fresh()


def _save(data: dict[str, Any]) -> None:
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_memory() -> dict[str, Any]:
    return _load()


def remember(text: str, category: str = "facts", source: str = "") -> dict[str, Any]:
    data = _load()
    if category not in {"facts", "routine"}:
        category = "facts"
    item = {"text": text.strip(), "created_at": datetime.now().isoformat(timespec="seconds")}
    if source:
        item["source"] = source  # V6.7.3: "auto" = aprendido sozinho nas conversas
    if item["text"] and item["text"] not in [x.get("text") for x in data[category]]:
        data[category].append(item)
        data[category] = data[category][-100:]
        _save(data)
    return item


def set_preference(key: str, value: str) -> None:
    data = _load()
    data["preferences"][key] = value.strip()
    _save(data)


def add_conversation(user: str, assistant: str) -> None:
    data = _load()
    data["conversation"].append({"user": user, "assistant": assistant, "at": datetime.now().isoformat(timespec="seconds")})
    data["conversation"] = data["conversation"][-20:]
    _save(data)


def clear_conversation(scope: str = "today") -> int:
    """V6.5.16: apaga a conversa guardada ("today" = só a de hoje; "all" = todo o período).
    Fatos, preferências e rotina (o que o JARVIS sabe sobre você) ficam. Devolve quantas trocas saíram."""
    data = _load()
    before = len(data["conversation"])
    if scope == "all":
        data["conversation"] = []
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        data["conversation"] = [c for c in data["conversation"] if not str(c.get("at", "")).startswith(today)]
    _save(data)
    return before - len(data["conversation"])


# V4.5: hora em que o JARVIS abriu; conversas antes disso são "de sessões anteriores"
_BOOT = datetime.now().isoformat(timespec="seconds")


def forget(text: str) -> int:
    """Esquece memórias que contêm `text` (sem diferenciar maiúsculas). Devolve quantas saíram."""
    import unicodedata

    def plain(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

    words = [w for w in plain(text).split() if w not in {"o", "a", "os", "as", "do", "da", "de", "meu", "minha", "que", "sobre"}]
    needle = " ".join(words)
    if not needle:
        return 0
    data = _load()
    before = len(data["facts"])
    data["facts"] = [x for x in data["facts"] if needle not in plain(x.get("text", ""))]
    removed = before - len(data["facts"])
    if removed:
        _save(data)
    return removed


def facts(limit: int = 10) -> list[str]:
    return [x["text"] for x in _load()["facts"][-limit:]]


def prompt_context() -> str:
    data = _load()
    parts = []
    if data["facts"]:
        parts.append("Memórias do usuário (ele te contou; use com naturalidade quando ajudar, sem listar): "
                     + "; ".join(x["text"] for x in data["facts"][-30:]))
    if data["preferences"]:
        parts.append("Preferências: " + "; ".join(f"{k}={v}" for k, v in data["preferences"].items()))
    if data["routine"]:
        parts.append("Rotinas conhecidas: " + "; ".join(x["text"] for x in data["routine"][-10:]))
    # V4.5: o que foi conversado nas sessões anteriores (o histórico da sessão atual já vai junto)
    previous = [c for c in data["conversation"] if c.get("at", "") < _BOOT][-6:]
    if previous:
        lines = [f"- Usuário: {c['user'][:160]} | JARVIS: {c['assistant'][:200]}" for c in previous]
        parts.append("Conversas recentes de sessões anteriores:\n" + "\n".join(lines))
    try:  # V6.7: humor recente (só para ajustar o tom)
        from modules import wellbeing

        mood = wellbeing.prompt_context()
        if mood:
            parts.append(mood)
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(parts)


# ------------------------------------------------------------------ V4.5: comandos de voz
import re as _re  # noqa: E402

_REMEMBER_RE = _re.compile(r"^(?:jarvis\s+)?(?:lembre|lembra|lembrar|aprenda|aprende|guarde|guarda|grave|grava|anote|anota)"
                           r"(?:\s+(?:na|em)\s+(?:sua\s+)?memoria)?\s+(?:que|disso:?)\s+(.+)$")
_RECALL_RE = _re.compile(r"^(?:jarvis\s+)?(?:o que (?:voce|vc) (?:lembra|sabe|aprendeu)(?: de mim| sobre mim)?|"
                         r"(?:mostra|mostre|quais sao) (?:as )?(?:suas )?memorias)\??$")
_FORGET_RE = _re.compile(r"^(?:jarvis\s+)?(?:esqueca|esquece|esquecer|apague da memoria|apaga da memoria)\s+(?:que\s+|de\s+|sobre\s+)?(.+)$")


def handle_voice(norm: str, original: str) -> Optional_str:
    """'lembre que meu time é o Palmeiras' / 'o que você lembra de mim?' / 'esqueça o dentista'."""
    m = _REMEMBER_RE.match(norm)
    if m:
        # Guarda o texto como foi dito (com acentos), sem o "lembre que"
        raw = _re.split(r"\b(?:que|disso:?)\s+", original, maxsplit=1, flags=_re.IGNORECASE)
        fact = (raw[1] if len(raw) > 1 else m.group(1)).strip().rstrip(".!")
        if not fact:
            return None
        remember(fact[0].upper() + fact[1:])
        return f"Guardado na memória, senhor: {fact}. Vou lembrar disso nas próximas conversas."
    if _RECALL_RE.match(norm):
        items = facts(12)
        if not items:
            return "Ainda não tenho memórias suas, senhor. Diga, por exemplo: lembre que eu treino às 18h."
        return ("Eu lembro que: " + "; ".join(items) + ". Se algo estiver errado ou o senhor preferir que eu "
                "não guarde, diga esqueça e o assunto.")
    m = _FORGET_RE.match(norm)
    if m:
        removed = forget(m.group(1))
        return (f"Pronto, esqueci {removed} memória{'s' if removed != 1 else ''} sobre isso, senhor."
                if removed else "Não achei nada sobre isso na memória, senhor.")
    return None
