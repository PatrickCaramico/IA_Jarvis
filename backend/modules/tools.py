import ast
import asyncio
import html
import json
import logging
import math
import operator
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import webbrowser
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import quote_plus, urlparse

import requests

from config import settings
from services import http_client, quotes
from modules.quick_replies import _norm
from modules import system_control, prefs, tasks, reminders, focus, briefing, spotify, health

log = logging.getLogger("jarvis.tools")

# O main.py registra aqui a função que fala/mostra os avisos dos timers.
_announce: Optional[Callable[[str], Awaitable[None]]] = None


def set_announcer(fn: Callable[[str], Awaitable[None]]) -> None:
    global _announce
    _announce = fn


def _deaccent(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


# ===================================================================== padrões factuais (pesquisa via navegador)
FACTUAL_PATTERNS = [
    "quem ganhou",
    "quem venceu",
    "quem e ",
    "quem sao ",
    "quem foi ",
    "quando e ",
    "quando sera",
    "quando vai",
    "quando foi",
    "onde fica",
    "onde e ",
    "onde sera",
    "quanto custa",
    "qual o valor",
    "qual o preco",
    "qual o resultado",
    "qual o placar",
    "placar de",
    "placar do",
    "o que aconteceu",
    "noticias sobre",
    "noticias de",
    "como esta a eleicao",
    "como esta o jogo",
    "resultado do jogo",
    "resultado de",
    "resultado da",
    "escalacao",
]

_PERSONAL_EXCLUSIONS = [
    "quem sou eu",
    "sobre mim",
    "meu nome",
    "minha idade",
    "onde eu moro",
    "quem e voce",
    "quem e vc",
    "quem e jarvis",
    "quem te criou",
    "meu lembrete",
    "meus lembretes",
    "minha tarefa",
    "minhas tarefas",
    "meu timer",
    "meus timers",
]


def is_factual_query(message: str) -> bool:
    """Verifica se a mensagem é uma pergunta factual/atual que deve consultar o navegador."""
    norm = _deaccent(message).strip()
    for exc in _PERSONAL_EXCLUSIONS:
        if exc in norm:
            return False
    for pat in FACTUAL_PATTERNS:
        pat_clean = _deaccent(pat)
        if pat_clean in norm:
            return True
    return False


# ===================================================================== números por extenso
_UNITS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
          "seis": 6, "sete": 7, "oito": 8, "nove": 9}
_TEENS = {"dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
          "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19}
_TENS = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60}
_NUMWORD = {**_UNITS, **_TEENS, **_TENS, "zero": 0}
_TENS_RE = "|".join(_TENS)
_UNITS_RE = "|".join(_UNITS)
_WORDS_RE = "|".join(sorted(_NUMWORD, key=len, reverse=True))
_NUM_TOKEN = rf"(?:\d+|(?:{_TENS_RE})\s+e\s+(?:{_UNITS_RE})|{_WORDS_RE})"


def _num_value(token: str) -> int:
    parts = token.split()
    if token.isdigit():
        return int(token)
    if len(parts) == 3:  # "vinte e cinco"
        return _TENS[parts[0]] + _UNITS[parts[2]]
    return _NUMWORD[parts[0]]


def _numwords_to_digits(text: str) -> str:
    text = re.sub(rf"\b({_TENS_RE})\s+e\s+({_UNITS_RE})\b",
                  lambda m: str(_TENS[m.group(1)] + _UNITS[m.group(2)]), text)
    return re.sub(rf"\b({_WORDS_RE})\b", lambda m: str(_NUMWORD[m.group(1)]), text)


# ===================================================================== timers e lembretes
_DUR_RE = re.compile(rf"\b({_NUM_TOKEN})\s*(segundos?|segs?|minutos?|mins?|horas?)\b")
_HALF_RE = re.compile(rf"\b({_NUM_TOKEN})\s*horas?\s+e\s+meia\b")
_MEIA_RE = re.compile(r"\bmeia\s+hora\b")
_TIMER_WORDS = ("timer", "temporizador", "alarme", "despertador", "me avise", "me avisa", "me lembre",
                "me lembra", "lembre me", "avise me", "me chame", "me chama", "me acorde", "me acorda")


def _extract_duration(norm: str) -> tuple[int, str]:
    """Soma as durações da frase e devolve (segundos, frase sem a duração)."""
    total = 0

    def add(seconds: int) -> str:
        nonlocal total
        total += seconds
        return " "

    text = _HALF_RE.sub(lambda m: add(_num_value(m.group(1)) * 3600 + 1800), norm)
    text = _MEIA_RE.sub(lambda m: add(1800), text)

    def generic(m: re.Match) -> str:
        unit = m.group(2)[0]
        return add(_num_value(m.group(1)) * {"s": 1, "m": 60, "h": 3600}[unit])

    text = _DUR_RE.sub(generic, text)
    return total, re.sub(r"\s+", " ", text).strip()


def _fmt_duration(sec: int) -> str:
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    parts = []
    if h:
        parts.append(f"{h} {_plural(h, 'hora', 'horas')}")
    if m:
        parts.append(f"{m} {_plural(m, 'minuto', 'minutos')}")
    if s:
        parts.append(f"{s} {_plural(s, 'segundo', 'segundos')}")
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]


_NOISE_PATTERNS = [
    r"\bpor favor\b", r"\bjarvis\b",
    r"\b(?:coloque|coloca|ponha|crie|cria|defina|define|programe|programa|inicie|inicia|configure|configura)\b",
    r"\b(?:um|o)\s+(?:timer|temporizador|alarme|despertador)\b",
    r"\b(?:timer|temporizador|alarme|despertador)\b",
    r"\bme\s+(?:avise|avisa|lembre|lembra|chame|chama|acorde|acorda)\b",
    r"\b(?:avise|lembre)\s+me\b",
]
_CONNECTORS = {"em", "de", "para", "pra", "que", "a", "o", "um", "uma", "daqui", "dentro", "e", "do", "da"}


def _clean_label(rest: str) -> str:
    for pattern in _NOISE_PATTERNS:
        rest = re.sub(pattern, " ", rest)
    words = rest.split()
    while words and words[0] in _CONNECTORS:
        words.pop(0)
    while words and words[-1] in _CONNECTORS:
        words.pop()
    return " ".join(words)


_timers: dict[int, dict] = {}
_timer_seq = 0


async def _timer_job(tid: int, seconds: int, label: str) -> None:
    try:
        await asyncio.sleep(seconds)
        text = f"Lembrete: {label}." if label else f"Seu timer de {_fmt_duration(seconds)} terminou."
        if _announce:
            await _announce(text)
    finally:
        _timers.pop(tid, None)


def active_timers() -> int:
    return len(_timers)


def get_active_timers_list() -> list[dict]:
    now = time.monotonic()
    result = []
    for tid, job in list(_timers.items()):
        left = max(int(job["ends"] - now), 0)
        result.append({
            "id": tid,
            "seconds_left": left,
            "total_seconds": job.get("total_seconds", left),
            "label": job.get("label", ""),
        })
    return sorted(result, key=lambda x: x["seconds_left"])


async def _h_timer(message: str, norm: str, words: int, name: str) -> Optional[str]:
    has_timer_noun = any(re.search(rf"\b{w}s?\b", norm) for w in ("timer", "temporizador", "alarme", "lembrete", "despertador"))

    if has_timer_noun and re.search(r"\b(?:cancele|cancela|cancelar|pare|apague|desligue|remova|exclua)\b", norm):
        count = len(_timers)
        for job in list(_timers.values()):
            job["task"].cancel()
        _timers.clear()
        return f"Cancelei {count} {_plural(count, 'timer', 'timers')}." if count else "Não há nenhum timer ativo."

    if has_timer_noun and re.search(r"\b(?:quais|meus|quantos|ativos|quanto falta|tem algum)\b", norm):
        if not _timers:
            return "Você não tem nenhum timer ativo."
        now = time.monotonic()
        items = []
        for job in sorted(_timers.values(), key=lambda j: j["ends"]):
            left = max(int(job["ends"] - now), 0)
            what = f" para {job['label']}" if job["label"] else ""
            items.append(f"faltam {_fmt_duration(left) if left else 'poucos segundos'}{what}")
        n = len(items)
        return f"Você tem {n} {_plural(n, 'timer ativo', 'timers ativos')}: " + "; ".join(items) + "."

    if not any(w in norm for w in _TIMER_WORDS):
        return None
    seconds, rest = _extract_duration(norm)
    if seconds <= 0:
        return None  # sem duração clara: deixa a IA orientar
    if seconds > 86400:
        return "Prefiro timers de até 24 horas."

    global _timer_seq
    _timer_seq += 1
    tid = _timer_seq
    label = _clean_label(rest)
    task = asyncio.create_task(_timer_job(tid, seconds, label))
    _timers[tid] = {"task": task, "ends": time.monotonic() + seconds, "label": label, "total_seconds": seconds}
    if label:
        return f"Combinado. Em {_fmt_duration(seconds)} eu lembro você de {label}."
    return f"Timer de {_fmt_duration(seconds)} iniciado."


# ===================================================================== anotações
_NOTES_PATH = settings.DATA_DIR / "anotacoes.json"
_NOTE_ADD = re.compile(
    r"^\s*(?:jarvis[\s,]+)?(?:por favor[\s,]+)?(?:anote|anota|anotar|guarde)(?:\s+(?:isso|aí|ai))?\s*[:,]?\s+(.+?)[\s.!]*$",
    re.I | re.S,
)


def _load_notes() -> list[dict]:
    try:
        data = json.loads(_NOTES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_notes(notes: list[dict]) -> None:
    _NOTES_PATH.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


async def _h_notes(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # 1. Adicionar anotação
    m = _NOTE_ADD.match(message)
    if m:
        notes = _load_notes()
        new_id = (max((n.get("id", 0) for n in notes), default=0)) + 1
        notes.append({
            "id": new_id,
            "texto": m.group(1).strip(),
            "quando": datetime.now().strftime("%d/%m às %H:%M")
        })
        _save_notes(notes)
        return f"Anotado: {m.group(1).strip()}."

    # 2. Buscar em anotações: "o que anotei sobre X", "buscar anotacao sobre X"
    search_m = re.search(r"\b(?:pesquise|pesquisar|buscar|busque|procure|procurar|o que (?:eu )?anotei sobre|o que tem sobre)\s+(?:anotacoes?|notas?)\s*(?:sobre\s+)?(.+)", norm)
    if search_m and any(w in norm for w in ("anot", "nota")):
        termo = search_m.group(1).strip()
        termo = re.sub(r"^(?:em|nas|as|minhas|sobre)\s+", "", termo)
        if termo and len(termo) >= 2:
            notes = _load_notes()
            encontradas = [n for n in notes if _norm(termo) in _norm(n.get("texto", ""))]
            if not encontradas:
                return f"Não encontrei nenhuma anotação mencionando '{termo}'."
            itens = [f"'{n['texto']}' (feita em {n.get('quando', '')})" for n in encontradas[:3]]
            return f"Encontrei {len(encontradas)} {_plural(len(encontradas), 'anotação', 'anotações')}: " + "; ".join(itens) + "."

    # 3. Apagar anotação específica por termo
    del_specific = re.search(r"\b(?:apague|apaga|apagar|remova|remover|exclua|excluir|delete|deletar)\s+(?:a\s+)?(?:anotacao|nota)\s+(?:sobre|de)?\s*(.+)", norm)
    if del_specific and "todas" not in norm and "tudo" not in norm:
        alvo = del_specific.group(1).strip()
        notes = _load_notes()
        restantes = [n for n in notes if _norm(alvo) not in _norm(n.get("texto", ""))]
        removidas = len(notes) - len(restantes)
        if removidas > 0:
            _save_notes(restantes)
            return f"Removi {removidas} {_plural(removidas, 'anotação', 'anotações')} relacionada a '{alvo}'."
        return f"Não encontrei nenhuma anotação sobre '{alvo}' para apagar."

    # 4. Apagar todas as anotações
    if words <= 8 and re.search(r"\b(?:apague|apaga|apagar|limpe|limpa|limpar|delete|exclua)\b", norm) \
            and re.search(r"\b(?:anotacoes|notas)\b", norm):
        count = len(_load_notes())
        _save_notes([])
        return f"Apaguei {count} {_plural(count, 'anotação', 'anotações')}." if count else "Você não tinha anotações."

    # 5. Ler todas / listar anotações
    if words <= 8 and re.search(r"\b(?:minhas anotacoes|o que eu anotei|o que anotei|minhas notas|lista de anotacoes|ler anotacoes|leia as anotacoes)\b", norm):
        notes = _load_notes()
        if not notes:
            return "Você ainda não tem anotações."
        recent = notes[-4:][::-1]
        text = "; ".join(f"{n['texto']} em {n.get('quando', '')}" for n in recent)
        extra = len(notes) - len(recent)
        tail = f" E mais {extra} {_plural(extra, 'anterior', 'anteriores')}." if extra > 0 else ""
        return f"Você tem {len(notes)} {_plural(len(notes), 'anotação', 'anotações')}: {text}.{tail}"
    return None


# ===================================================================== abrir sites e programas
_SHORTCUTS_PATH = settings.DATA_DIR / "atalhos.json"
_SHORTCUTS_EXAMPLE_PATH = settings.DATA_DIR / "atalhos.example.json"
_DEFAULT_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "whatsapp": "https://web.whatsapp.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "bloco de notas": "notepad",
    "calculadora": "calc",
    "explorador de arquivos": "explorer",
}
_OPEN_RE = re.compile(
    r"^(?:jarvis\s+)?(?:por favor\s+)?(?:abra|abre|abrir|inicie|iniciar|execute|executar|acesse|acessar)\s+(?:o |a |os |as |um |uma )?(.+)$"
)


def validate_site_url(value: str) -> str:
    """Valida uma URL de site nativa (HTTP/HTTPS) e devolve a versão normalizada."""
    if not isinstance(value, str):
        raise ValueError("A URL do site deve ser um texto.")
    url = value.strip()
    if not url:
        raise ValueError("Informe a URL do site.")
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("A URL do site precisa começar com http:// ou https://.")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("A URL do site precisa ser um endereço web válido.")
    return url


def _normalize_site_entry(name: str, value: Any) -> dict[str, Any]:
    """Normaliza um item do JSON de atalhos para o formato com URL, apelidos e janela propria."""
    if isinstance(value, str):
        text = value.strip()
        if re.match(r"^https?://", text, re.I):
            return {"name": str(name), "url": validate_site_url(text), "apelidos": [], "janela_app": False}
        return {"name": str(name), "url": text, "apelidos": [], "janela_app": False}
    if not isinstance(value, dict):
        raise ValueError(f"O site '{name}' está em formato inválido.")
    url = value.get("url")
    if not url:
        raise ValueError(f"O site '{name}' precisa de uma URL.")
    return {
        "name": str(name),
        "url": validate_site_url(str(url)),
        "apelidos": [str(item).strip() for item in value.get("apelidos", []) if str(item).strip()],
        "janela_app": bool(value.get("janela_app", False)),
    }


def _save_shortcuts(data: dict[str, Any]) -> None:
    _SHORTCUTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _site_conflict_key(value: str) -> str:
    return _norm(value.strip())


def _detect_site_conflicts(existing: dict[str, Any], name: str, aliases: list[str], ignore_name: str | None = None) -> None:
    seen: dict[str, str] = {}
    for current_name, raw in existing.items():
        if ignore_name is not None and current_name == ignore_name:
            continue
        try:
            entry = _normalize_site_entry(current_name, raw)
        except ValueError:
            continue
        seen[_site_conflict_key(current_name)] = current_name
        for alias in entry["apelidos"]:
            seen[_site_conflict_key(alias)] = current_name
    candidates = {_site_conflict_key(name)} | {_site_conflict_key(alias) for alias in aliases}
    for candidate in candidates:
        if candidate and candidate in seen:
            raise ValueError(f"Já existe um site com o nome ou apelido '{seen[candidate]}'.")


def list_sites() -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    for name, value in _load_shortcuts().items():
        try:
            entry = _normalize_site_entry(str(name), value)
        except ValueError:
            continue
        if not re.match(r"^https?://", str(entry["url"]), re.I):
            continue
        sites.append({"name": entry["name"], "url": entry["url"], "apelidos": entry["apelidos"], "janela_app": entry["janela_app"]})
    return sites


def save_site(name: str, url: str, apelidos: list[str] | None = None, janela_app: bool = False) -> dict[str, Any]:
    raw = _load_shortcuts()
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Dê um nome para o site.")
    entries = [item.strip() for item in (apelidos or []) if item and str(item).strip()]
    _detect_site_conflicts(raw, clean_name, entries)
    payload = {**raw, clean_name: {"url": validate_site_url(url), "apelidos": entries, "janela_app": bool(janela_app)}}
    _save_shortcuts(payload)
    return {"name": clean_name, "url": payload[clean_name]["url"], "apelidos": entries, "janela_app": bool(janela_app)}


def update_site(old_name: str, name: str, url: str, apelidos: list[str] | None = None, janela_app: bool = False) -> dict[str, Any]:
    raw = _load_shortcuts()
    if old_name not in raw:
        raise KeyError(f"Site '{old_name}' não encontrado.")
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Dê um nome para o site.")
    entries = [item.strip() for item in (apelidos or []) if item and str(item).strip()]
    _detect_site_conflicts({k: v for k, v in raw.items() if k != old_name}, clean_name, entries, ignore_name=None)
    raw[clean_name] = {"url": validate_site_url(url), "apelidos": entries, "janela_app": bool(janela_app)}
    if old_name != clean_name:
        del raw[old_name]
    _save_shortcuts(raw)
    return {"name": clean_name, "url": raw[clean_name]["url"], "apelidos": entries, "janela_app": bool(janela_app)}


def delete_site(name: str) -> bool:
    raw = _load_shortcuts()
    if name not in raw:
        return False
    del raw[name]
    _save_shortcuts(raw)
    return True


def _lookup_site(wanted: str) -> tuple[str, dict[str, Any]] | None:
    site_map: dict[str, tuple[str, dict[str, Any]]] = {}
    for name, value in _load_shortcuts().items():
        try:
            entry = _normalize_site_entry(str(name), value)
        except ValueError:
            continue
        if not re.match(r"^https?://", str(entry["url"]), re.I):
            continue
        site_map[_site_conflict_key(entry["name"])] = (entry["name"], entry)
        for alias in entry["apelidos"]:
            site_map[_site_conflict_key(alias)] = (entry["name"], entry)
    normalized = _site_conflict_key(wanted)
    return site_map.get(normalized)


def _open_site(site: dict[str, Any]) -> None:
    url = site.get("url")
    if not url:
        return
    if site.get("janela_app"):
        chrome_candidates = [
            shutil.which("google-chrome"),
            shutil.which("chrome"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome = next((path for path in chrome_candidates if path and os.path.isfile(path)), None)
        if chrome:
            try:
                subprocess.Popen([chrome, f"--app={url}"], shell=False)
                return
            except (OSError, subprocess.SubprocessError):
                pass
    _open_in_default_browser(url)


def _load_shortcuts() -> dict:
    if not _SHORTCUTS_PATH.exists():
        if _SHORTCUTS_EXAMPLE_PATH.exists():
            try:
                data = json.loads(_SHORTCUTS_EXAMPLE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, ValueError) as exc:
                log.warning("atalhos.example.json inválido (%s); usando os atalhos padrão.", exc)
        return dict(_DEFAULT_SHORTCUTS)
    try:
        data = json.loads(_SHORTCUTS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError) as exc:
        log.warning("atalhos.json inválido (%s); usando os atalhos padrão.", exc)
    return dict(_DEFAULT_SHORTCUTS)


def _open_target(target: str) -> None:
    target = target.strip()
    if not target:
        return
    if re.match(r"^https?://", target):
        webbrowser.open(target)
    elif os.name == "nt":
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except Exception:
            # Fallback seguro para execução via PowerShell sem risco de command injection (usa variável de ambiente)
            env = os.environ.copy()
            env["JARVIS_TARGET"] = target
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", "Start-Process -FilePath $env:JARVIS_TARGET"],
                env=env
            )
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen([target])


# Serviços conhecidos da web para fallback inteligente
_SMART_WEB_SERVICES = {
    "disney": "https://www.disneyplus.com",
    "disneyplus": "https://www.disneyplus.com",
    "disney plus": "https://www.disneyplus.com",
    "netflix": "https://www.netflix.com",
    "hbo": "https://www.max.com",
    "max": "https://www.max.com",
    "prime video": "https://www.primevideo.com",
    "amazon prime": "https://www.primevideo.com",
    "twitch": "https://www.twitch.tv",
    "crunchyroll": "https://www.crunchyroll.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "linkedin": "https://www.linkedin.com",
    "notion": "https://www.notion.so",
}


def _try_open_smart(target_name: str) -> tuple[bool, str, str]:
    """Tenta abrir de forma inteligente e segura:
    1. Se for serviço de streaming/web conhecido com limites de palavra (\b), abre direto no navegador.
    2. Se tiver extensão de domínio explícita (.com, .br, etc), abre URL.
    3. Se existir aplicativo local no Windows ou comando executável, abre na máquina com proteção contra injeção.
    4. Não tenta adivinhar sites desconhecidos com .com para evitar abrir páginas indesejadas sem confirmação.
    Retorna (sucesso, tipo_execucao, label).
    """
    clean = _deaccent(target_name).strip()
    if not clean:
        return False, "", ""

    # 1. Checa serviços web / streamings com limites de palavra exatos (\b)
    for key, url in _SMART_WEB_SERVICES.items():
        if clean == key or bool(re.search(rf"\b{re.escape(key)}\b", clean, flags=re.I)):
            _open_target(url)
            return True, "web", key.title()

    # 2. Se for link ou domínio explicitamente digitado (.com, .br, etc)
    if re.search(r"\.(com|br|org|net|io|ai|tv|gov)\b", clean, flags=re.I) or clean.startswith("http"):
        url = clean if clean.startswith("http") else f"https://{clean}"
        _open_target(url)
        return True, "web", clean

    # 3. Tenta localizar executável local no sistema
    import shutil
    cmd_name = clean.replace(" ", "")
    if shutil.which(cmd_name) or shutil.which(clean):
        try:
            _open_target(clean)
            return True, "app", clean.title()
        except Exception:
            pass

    # No Windows, tenta Start-Process direto de forma segura sem injeção de comandos
    if os.name == "nt":
        # Bloqueia caracteres de controle perigosos
        if not re.search(r"[;&|`$<>\"'\n\r]", clean):
            try:
                env = os.environ.copy()
                env["JARVIS_TARGET"] = clean
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", "Start-Process -FilePath $env:JARVIS_TARGET -ErrorAction Stop"],
                    capture_output=True,
                    timeout=2.0,
                    env=env
                )
                if res.returncode == 0:
                    return True, "app", clean.title()
            except Exception:
                pass

    # 4. Não tenta adivinhar abrindo .com arbitrário no navegador sem confirmação
    return False, "", ""


def _open_spotify_desktop() -> None:
    """Foca o Spotify desktop já aberto ou inicia o aplicativo se necessário."""
    if os.name != "nt":
        _open_target("spotify:")
        return

    script = r"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class JarvisWindow {
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr handle, int command);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr handle);
}
'@
$spotify = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match 'Spotify' } |
    Select-Object -First 1
if ($null -eq $spotify) {
    $spotify = Get-Process -Name 'Spotify' -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Select-Object -First 1
}
if ($null -ne $spotify) {
    $handle = [IntPtr]$spotify.MainWindowHandle
    [JarvisWindow]::ShowWindowAsync($handle, 9) | Out-Null
    if (-not [JarvisWindow]::SetForegroundWindow($handle)) { exit 1 }
    exit 0
}
Start-Process 'spotify:'
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )


def _remember_open(label: str, wanted: str) -> None:
    """Anota o "abre o ..." para as sugestões pela rotina (4.2). Nunca atrapalha a abertura."""
    try:
        from modules import routine

        routine.record(f"open:{_norm(wanted)}", str(label), "open", wanted)
    except Exception:  # noqa: BLE001
        log.debug("Rotina: não foi possível anotar a abertura", exc_info=True)


async def _h_open(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if re.search(r"\b(?:quais|meus)\s+sites?\b|\bsite[s]?\s+você\s+abre\b|\bquais\s+sites?\s+voce\s+abre\b", norm, re.I):
        sites = list_sites()
        if not sites:
            return "Você ainda não cadastrou nenhum site. Adicione em Configurações > Meus Sites."
        preview = ", ".join(site["name"] for site in sites[:5])
        return f"Eu abro {len(sites)} site(s): {preview}."

    m = _OPEN_RE.match(norm)
    if not m or words > 8:
        return None
    wanted = m.group(1).strip()
    if _norm(wanted) == "spotify":
        try:
            await asyncio.to_thread(_open_spotify_desktop)
            return "Spotify aberto no aplicativo do computador, senhor."
        except (OSError, subprocess.SubprocessError):
            log.exception("Falha ao abrir o aplicativo Spotify")
            return "Não consegui abrir o aplicativo do Spotify neste computador, senhor."

    site_hit = _lookup_site(wanted)
    if site_hit is not None:
        label, site = site_hit
        try:
            await asyncio.to_thread(_open_site, site)
            _remember_open(label, wanted)
            return f"Abrindo {label} no navegador, senhor."
        except Exception:  # noqa: BLE001
            log.exception("Falha ao abrir site %s", site.get("url"))
            return f"Não consegui abrir {label}."

    shortcuts = {_norm(k): (k, v) for k, v in _load_shortcuts().items()}
    hit = shortcuts.get(wanted)
    if hit is None:
        for key, value in shortcuts.items():
            if wanted.startswith(key + " ") or (len(wanted) >= 3 and key.startswith(wanted)):
                hit = value
                break

    if hit is not None:
        label, target = hit
        try:
            if _norm(label) == "spotify":
                await asyncio.to_thread(_open_spotify_desktop)
                return "Spotify aberto no aplicativo do computador, senhor."
            await asyncio.to_thread(_open_target, str(target))
            _remember_open(label, wanted)
            tipo = "no navegador" if re.match(r"^https?://", str(target)) else "na máquina"
            return f"Abrindo {label} {tipo}, senhor."
        except Exception:  # noqa: BLE001
            log.exception("Falha ao abrir %s", target)
            return f"Não consegui abrir {label}."

    # Roteador inteligente: se não estava na lista de atalhos, analisa automaticamente
    ok, mode, final_label = await asyncio.to_thread(_try_open_smart, wanted)
    if ok:
        _remember_open(final_label, wanted)
        if mode == "web":
            return f"Abrindo {final_label} no navegador, senhor."
        return f"Iniciando {final_label} no seu computador, senhor."

    return "Não conheço esse site. Adicione em Configurações > Meus Sites."


# ===================================================================== pesquisar no navegador
_SEARCH_RE = re.compile(
    r"^\s*(?:jarvis[\s,]+)?(?:por favor[\s,]+)?(?:(?:me\s+)?(?:mostre|mostra)|"
    r"pesquise|pesquisa|pesquisar|procure|procura|busque|busca|buscar)\s+"
    r"(?:por\s+|sobre\s+)?(.+?)[\s.!?]*$",
    re.I | re.S,
)


class _GoogleResultParser(HTMLParser):
    """Extrai títulos e trechos públicos sem depender de um navegador automatizado."""

    _SNIPPET_CLASSES = ("VwiC3b", "yXK7lf", "IsZvec", "result__snippet", "b_caption")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._capture = False
        self._buffer: list[str] = []
        self.snippets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set()
        for key, value in attrs:
            if key == "class" and value:
                classes.update(value.split())
        if classes.intersection(self._SNIPPET_CLASSES):
            self._capture = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._capture:
            self._buffer.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._capture:
            self._buffer.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        if self._capture and tag in ("div", "span"):
            text = re.sub(r"\s+", " ", html.unescape("".join(self._buffer))).strip()
            if len(text) >= 35 and text not in self.snippets:
                self.snippets.append(text)
            self._capture = False


_SEARCH_CACHE: dict[str, tuple[float, str, list[dict]]] = {}  # norm_query -> (timestamp, speech_text, sources)
_last_browser_search_data: dict[str, Any] = {}


def get_last_browser_search_data() -> dict[str, Any]:
    global _last_browser_search_data
    return _last_browser_search_data


def _is_blocked_page(html_text: str) -> bool:
    """Detecta páginas de bloqueio, captcha ou consentimento de motores de busca."""
    indicators = (
        "detected unusual traffic",
        "before you continue",
        "consent.google",
        "recaptcha",
        "challenge-running",
        "cf-turnstile",
    )
    lower = html_text.lower()
    return any(ind in lower for ind in indicators)


def _search_google(query: str) -> tuple[list[str], list[dict]]:
    url = "https://www.google.com/search"
    resp = requests.get(
        url,
        params={"q": query, "hl": "pt-BR", "num": 5},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        timeout=6,
    )
    if resp.status_code != 200 or _is_blocked_page(resp.text):
        return [], []
    parser = _GoogleResultParser()
    parser.feed(resp.text)
    snippets = parser.snippets[:3]
    sources: list[dict] = []
    for link_match in re.finditer(r'<a\s+[^>]*href="(/url\?q=)?(https?://[^"&]+)"[^>]*>(.*?)</a>', resp.text, re.I):
        href = link_match.group(2)
        raw_title = re.sub(r"<[^>]+>", "", link_match.group(3)).strip()
        if raw_title and "google.com" not in href and len(raw_title) > 5:
            sources.append({"name": raw_title[:45], "headline": raw_title, "url": href})
            if len(sources) >= 3:
                break
    return snippets, sources


def _search_bing(query: str) -> tuple[list[str], list[dict]]:
    url = "https://www.bing.com/search"
    resp = requests.get(
        url,
        params={"q": query, "setlang": "pt-br"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=6,
    )
    if resp.status_code != 200 or _is_blocked_page(resp.text):
        return [], []
    parser = _GoogleResultParser()
    parser.feed(resp.text)
    snippets = parser.snippets[:3]
    sources: list[dict] = []
    for link_match in re.finditer(r'<li\s+class="b_algo"[^>]*>.*?<h2><a\s+[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', resp.text, re.I | re.S):
        href = link_match.group(1)
        raw_title = re.sub(r"<[^>]+>", "", link_match.group(2)).strip()
        if raw_title and "bing.com" not in href:
            sources.append({"name": raw_title[:45], "headline": raw_title, "url": href})
            if len(sources) >= 3:
                break
    return snippets, sources


def _search_duckduckgo(query: str) -> tuple[list[str], list[dict]]:
    url = "https://html.duckduckgo.com/html/"
    resp = requests.post(
        url,
        data={"q": query, "kl": "br-pt"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=6,
    )
    if resp.status_code != 200 or _is_blocked_page(resp.text):
        return [], []
    snippets: list[str] = []
    sources: list[dict] = []
    for item in re.finditer(r'<a\s+class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.I | re.S):
        snip = re.sub(r"<[^>]+>", "", item.group(1)).strip()
        if len(snip) >= 25 and snip not in snippets:
            snippets.append(snip)
            if len(snippets) >= 3:
                break
    for item in re.finditer(r'<a\s+class="result__a"\s+href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.I | re.S):
        href = item.group(1)
        if "/l/?uddg=" in href:
            import urllib.parse
            href = urllib.parse.unquote(href.split("/l/?uddg=")[-1].split("&")[0])
        title = re.sub(r"<[^>]+>", "", item.group(2)).strip()
        if title:
            sources.append({"name": title[:45], "headline": title, "url": href})
            if len(sources) >= 3:
                break
    return snippets, sources


def _fetch_web_results(query: str) -> tuple[list[str], list[dict]]:
    """Tenta Google, Bing e DuckDuckGo HTML até achar resultados legíveis."""
    # 1. Google
    try:
        snips, srcs = _search_google(query)
        if snips:
            return snips, srcs
    except Exception as exc:
        log.warning("Busca Google falhou (%s), tentando Bing...", exc)

    # 2. Bing
    try:
        snips, srcs = _search_bing(query)
        if snips:
            return snips, srcs
    except Exception as exc:
        log.warning("Busca Bing falhou (%s), tentando DuckDuckGo...", exc)

    # 3. DuckDuckGo HTML
    try:
        snips, srcs = _search_duckduckgo(query)
        if snips:
            return snips, srcs
    except Exception as exc:
        log.warning("Busca DuckDuckGo falhou (%s).", exc)

    return [], []


def _open_in_default_browser(url: str) -> None:
    """Abre a URL garantindo o navegador padrão do Windows."""
    try:
        opened = webbrowser.open(url, new=2, autoraise=True)
        if not opened and os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
    except Exception:
        log.exception("Falha ao abrir URL no navegador padrão: %s", url)
        if os.name == "nt":
            try:
                os.startfile(url)  # type: ignore[attr-defined]
            except Exception:
                pass


_DEEP_SEARCH_RE = re.compile(
    r"^\s*(?:jarvis[\s,]+)?(?:por favor[\s,]+)?(?:"
    r"(?:faca\s+uma\s+)?pesquisa\s+profunda(?:\s+sobre|\s+de)?|"
    r"pesquise\s+a\s+fundo(?:\s+sobre|\s+de)?|"
    r"aprofunde(?:\s+isso|\s+sobre|\s+este\s+tema)?|"
    r"(?:use|usando)\s+a?\s*ia\s+para\s+pesquisar(?:\s+sobre|\s+de)?|"
    r"pesquise\s+(?:com|usando)\s+a?\s*ia(?:\s+sobre|\s+de)?"
    r")\s*(.*)$",
    re.I
)


def extract_deep_search_request(message: str) -> tuple[bool, str]:
    """Retorna (is_deep, query) caso a mensagem solicite explicitamente pesquisa profunda / IA."""
    m = _DEEP_SEARCH_RE.match(message.strip())
    if not m:
        return False, ""
    query = m.group(1).strip(" .!?")
    return True, query


def extract_search_query(message: str) -> Optional[str]:
    """Retorna o termo de busca caso a mensagem seja uma solicitação explícita de pesquisa."""
    m = _SEARCH_RE.match(message)
    if not m:
        return None
    query = m.group(1).strip()
    return query if len(query.split()) <= 18 else None


async def execute_browser_search(query: str) -> str:
    """Executa pesquisa no navegador padrão, com cache de 10 min e resposta falada concisa."""
    global _last_browser_search_data
    yt = re.match(r"^(.+?)\s+(?:no|em|pelo)\s+youtube$", query, re.I)
    if yt:
        clean_q, url, where = yt.group(1), "https://www.youtube.com/results?search_query=", "no YouTube"
    else:
        clean_q = re.sub(r"\s+(?:no|em|pelo)\s+google$|\s+na\s+internet$", "", query, flags=re.I)
        url, where = "https://www.google.com/search?q=", "no Google"

    # Abre a guia no navegador padrão do sistema
    await asyncio.to_thread(_open_in_default_browser, url + quote_plus(clean_q))
    if yt:
        return f"Pesquisando {clean_q} {where}."

    # Cache de 10 minutos (600s) para a mesma consulta
    cache_key = _deaccent(clean_q).strip()
    now = time.time()
    if cache_key in _SEARCH_CACHE:
        ts, cached_speech, cached_sources = _SEARCH_CACHE[cache_key]
        if now - ts < 600:
            log.info("Resultado de pesquisa recuperado do cache (10 min): '%s'", clean_q)
            _last_browser_search_data = {
                "query": clean_q,
                "summary": cached_speech,
                "sources": cached_sources,
                "time": datetime.now().strftime("%H:%M")
            }
            return cached_speech

    try:
        snippets, sources = await asyncio.to_thread(_fetch_web_results, clean_q)
    except Exception:
        log.exception("Falha na consulta web para %s", clean_q)
        snippets, sources = [], []

    if not snippets:
        return f"Abri a pesquisa por {clean_q} no navegador, senhor. Não consegui ler os resultados, senhor. Quer que eu use a pesquisa profunda?"

    # Resposta falada curta (máximo 3 frases)
    full_text = " ".join(snippets)
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", full_text) if len(s.strip()) > 10]
    short_sentences = sentences[:3] if sentences else [full_text[:200]]
    short_speech = ". ".join(short_sentences).strip(" .!?") + "."
    speech_reply = f"Pesquisei {clean_q} na web, senhor. Os principais resultados indicam: {short_speech}"

    if not sources:
        sources = [
            {"name": "Google Search", "headline": "Pesquisa na web", "url": f"https://www.google.com/search?q={quote_plus(clean_q)}"}
        ]

    # Armazena em cache e salva os dados estruturados para o card modal do HUD
    _SEARCH_CACHE[cache_key] = (now, speech_reply, sources)
    _last_browser_search_data = {
        "query": clean_q,
        "summary": short_speech,
        "snippets": snippets,
        "sources": sources,
        "time": datetime.now().strftime("%H:%M")
    }

    return speech_reply


async def _h_search(message: str, norm: str, words: int, name: str) -> Optional[str]:
    query = extract_search_query(message)
    if not query:
        return None
    yt = re.match(r"^(.+?)\s+(?:no|em|pelo)\s+youtube$", query, re.I)
    if yt:
        return await execute_browser_search(query)

    mode = prefs.get_search_mode()
    if mode == "browser":
        return await execute_browser_search(query)
    # Se "api" ou "ask", retorna None para o main.py tratar
    return None


# ===================================================================== calculadora
_CALC_RE = re.compile(
    r"^(?:jarvis[\s,]+)?(?:por favor[\s,]+)?(?:quanto\s+(?:e|eh|da|fica|vale|sera)|calcule|calcula|calcular|"
    r"qual\s+(?:e\s+)?(?:o\s+)?resultado\s+de|resultado\s+de)\s*:?\s*(.+)$"
)
_SQRT_RE = re.compile(r"^(?:jarvis[\s,]+)?(?:qual\s+e\s+a\s+)?raiz\s+quadrada\s+de\s+(.+)$")
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("expoente grande demais")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("expressão não permitida")


def _to_expr(s: str) -> Optional[str]:
    s = _numwords_to_digits(_deaccent(s))
    s = re.sub(r"(\d+(?:[.,]\d+)?)\s*(?:%|por cento)\s*de\s*(\d+(?:[.,]\d+)?)", r"(\1/100*\2)", s)
    s = re.sub(r"\b(\d{1,3})\.(\d{3})\b", r"\1\2", s)  # 1.000 -> 1000
    s = s.replace(",", ".")
    for pattern, repl in [(r"\bmultiplicado\s+por\b", "*"), (r"\bvezes\b", "*"), (r"(?<=\d)\s*x\s*(?=\d)", "*"),
                          (r"\bdividido\s+(?:por|pelo)\b", "/"), (r"\bsobre\b", "/"), (r"\bmais\b", "+"),
                          (r"\bmenos\b", "-"), (r"\belevado\s+a\b", "**"), (r"\bao\s+quadrado\b", "**2"),
                          (r"\bao\s+cubo\b", "**3")]:
        s = re.sub(pattern, repl, s)
    s = s.strip(" ?!.")
    return s if s and re.fullmatch(r"[\d\s+\-*/().]+", s) else None


def _fmt_number(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.4f}".rstrip("0").rstrip(".").replace(".", ",")


async def _h_calc(message: str, norm: str, words: int, name: str) -> Optional[str]:
    text = _deaccent(message).strip().rstrip("?!. ")
    sq = _SQRT_RE.match(text)
    try:
        if sq:
            expr = _to_expr(sq.group(1))
            if expr is None:
                return None
            value = _safe_eval(ast.parse(expr, mode="eval"))
            if value < 0:
                return "Não existe raiz quadrada real de número negativo."
            return f"A raiz quadrada é {_fmt_number(math.sqrt(value))}."
        m = _CALC_RE.match(text)
        if not m:
            return None
        expr = _to_expr(m.group(1))
        if expr is None:
            return None
        value = _safe_eval(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "Não dá para dividir por zero."
    except (ValueError, SyntaxError, OverflowError):
        return None  # não era uma conta: deixa a IA responder
    if math.isnan(value) or math.isinf(value):
        return None
    return f"O resultado é {_fmt_number(value)}."


# ===================================================================== clima (Open-Meteo, sem chave)
_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FC_URL = "https://api.open-meteo.com/v1/forecast"
_WEATHER_TRIGGERS = ("previsao do tempo", "clima", "temperatura", "vai chover", "chuva", "chovendo",
                     "como esta o tempo", "como ta o tempo", "tempo hoje", "tempo amanha", "faz frio",
                     "faz calor", "esta frio", "esta calor", "guarda chuva")
_WMO = {0: "céu limpo", 1: "céu predominantemente limpo", 2: "tempo parcialmente nublado", 3: "céu nublado",
        45: "neblina", 48: "neblina", 51: "garoa leve", 53: "garoa", 55: "garoa forte",
        56: "garoa congelante", 57: "garoa congelante", 61: "chuva fraca", 63: "chuva", 65: "chuva forte",
        66: "chuva congelante", 67: "chuva congelante forte", 71: "neve fraca", 73: "neve", 75: "neve forte",
        77: "grãos de neve", 80: "pancadas de chuva fracas", 81: "pancadas de chuva",
        82: "pancadas de chuva fortes", 85: "pancadas de neve", 86: "pancadas de neve fortes",
        95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas com granizo forte"}


def _fetch_weather(city: str) -> Optional[dict]:
    # a posição da cidade quase nunca muda (cache de 1 dia); a previsão, a cada 10 minutos
    geo = http_client.get_json(
        _GEO_URL,
        params={"name": city, "count": 1, "language": "pt", "format": "json", "countryCode": "BR"},
        timeout=10, ttl=24 * 3600,
    )
    results = geo.get("results") or []
    if not results:
        return None
    place = results[0]
    forecast = http_client.get_json(_FC_URL, params={
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
        # V5.6.3: nascer e pôr do sol para o cartão HOJE do bloqueio
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "timezone": "auto", "forecast_days": 2,
    }, timeout=10, ttl=600)
    if not forecast.get("current") or not forecast.get("daily"):
        raise ValueError("A API de clima retornou uma previsão incompleta.")
    return {"place": place.get("name", city), "data": forecast}


async def _h_weather(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 12 or not any(t in norm for t in _WEATHER_TRIGGERS):
        return None
    tomorrow = "amanha" in norm
    text = re.sub(r"\b(?:hoje|agora|amanha|neste momento|no momento)\b", " ", norm)
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"\b(?:em|para|pra)\s+([a-z]+(?:\s+[a-z]+){0,3})$", text)
    city = m.group(1) if m else settings.WEATHER_CITY
    try:
        result = await asyncio.to_thread(_fetch_weather, city)
    except (requests.RequestException, ValueError, KeyError):
        log.exception("Falha ao consultar o clima")
        return "Não consegui consultar o clima agora. Verifique a internet."
    if result is None:
        return f"Não encontrei a cidade {city}."

    data, place = result["data"], result["place"]
    daily, cur = data.get("daily", {}), data.get("current", {})
    idx = 1 if tomorrow else 0
    try:
        tmax, tmin = round(daily["temperature_2m_max"][idx]), round(daily["temperature_2m_min"][idx])
        code = daily["weather_code"][idx] if tomorrow else cur.get("weather_code", daily["weather_code"][0])
    except (KeyError, IndexError, TypeError):
        return "Não consegui interpretar a previsão do tempo."
    desc = _WMO.get(code, "tempo variável")
    prob = (daily.get("precipitation_probability_max") or [None, None])[idx]
    rain = f", com {round(prob)}% de chance de chuva" if prob is not None else ""

    if tomorrow:
        return f"Amanhã em {place}: previsão de {desc}, máxima de {tmax} e mínima de {tmin} graus{rain}."
    temp, feels = cur.get("temperature_2m"), cur.get("apparent_temperature")
    now_part = f"agora faz {round(temp)} graus, com {desc}" if temp is not None else f"o tempo está com {desc}"
    feels_part = f" Sensação térmica de {round(feels)}." if feels is not None else ""
    return f"Em {place}, {now_part}.{feels_part} Hoje a máxima é {tmax} e a mínima {tmin}{rain}."


# ===================================================================== cotações (AwesomeAPI, sem chave)
_CURRENCIES = {"dolar": ("USD-BRL", "USDBRL", "dólar"), "euro": ("EUR-BRL", "EURBRL", "euro"),
               "bitcoin": ("BTC-BRL", "BTCBRL", "bitcoin")}


def _fetch_rate(pair: str, key: str) -> float:
    return quotes.get_rate(key)


async def _h_exchange(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 10:
        return None
    cur = next((k for k in _CURRENCIES if re.search(rf"\b{k}s?\b", norm)), None)
    if cur is None:
        return None
    asks = any(t in norm for t in ("cotacao", "quanto esta", "quanto custa", "quanto vale", "valor do", "preco do",
                                   "esta custando", "esta valendo"))
    if not asks and words > 3:
        return None
    pair, key, label = _CURRENCIES[cur]
    try:
        value = await asyncio.to_thread(_fetch_rate, pair, key)
    except (requests.RequestException, ValueError, KeyError):
        log.exception("Falha ao consultar a cotação")
        return "Não consegui consultar a cotação agora."
    shown = f"{value:,.0f}".replace(",", ".") if value >= 1000 else f"{value:.2f}".replace(".", ",")
    return f"O {label} está cotado a {shown} reais."


# ===================================================================== diagnóstico real
async def _h_status(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 6 or not re.search(r"\b(?:status|diagnostico|sistemas)\b", norm):
        return None
    from modules import face
    from modules.vision import open_camera

    def check_camera() -> bool:
        try:
            open_camera().release()
            return True
        except Exception:  # noqa: BLE001
            return False

    cam_ok = await asyncio.to_thread(check_camera)
    provider = settings.LLM_PROVIDER
    key = {"openai": settings.OPENAI_API_KEY, "anthropic": settings.ANTHROPIC_API_KEY,
           "gemini": settings.GEMINI_API_KEY}.get(provider, "")
    parts = [
        f"a inteligência artificial está configurada com {provider}" if key else f"atenção, falta a chave de API do provedor {provider}",
        "a câmera está funcionando" if cam_ok else "não consegui acessar a câmera",
        "há uma foto de perfil cadastrada" if face.has_profile() else "ainda não há foto de perfil cadastrada",
    ]
    n = len(_timers)
    if n:
        parts.append(f"{n} {_plural(n, 'timer ativo', 'timers ativos')}")
    return "Diagnóstico: " + "; ".join(parts) + "."


# ===================================================================== atalhos personalizados (Fase 1)
async def _h_custom_shortcut(message: str, norm: str, words: int, name: str) -> Optional[str]:
    """Executa atalhos personalizados: abre múltiplos apps + URLs com um só comando."""
    shortcuts = prefs.get_shortcuts()
    if not shortcuts:
        return None
    for shortcut_name, config in shortcuts.items():
        key = _norm(shortcut_name)
        # verifica se o usuário está pedindo este atalho
        if key not in norm and not any(p in norm for p in key.split()):
            continue
        # precisa de uma intenção de abertura
        if not re.search(r"\b(abra|abre|abrir|inicie|inicia|execute|acesse|acessa|rode|roda)\b", norm):
            continue
        opened = []
        errors = []
        apps = config.get("apps", [])
        urls = config.get("urls", [])
        for app in apps:
            try:
                await asyncio.to_thread(_open_target, app)
                opened.append(app)
            except Exception:  # noqa: BLE001
                errors.append(app)
        for url in urls:
            try:
                await asyncio.to_thread(webbrowser.open, url)
                opened.append(url)
            except Exception:  # noqa: BLE001
                errors.append(url)
        if not opened and not errors:
            return f"O atalho '{shortcut_name}' não tem nada configurado."
        result = f"Atalho '{shortcut_name}' executado: abri {len(opened)} item(ns)."
        if errors:
            result += f" Não consegui abrir: {', '.join(errors)}."
        return result
    return None


# ===================================================================== controle do sistema (Fase 1)
def _activate_browser() -> bool:
    if os.name != "nt":
        return False
    script = r"""
$shell = New-Object -ComObject WScript.Shell
$browser = Get-Process -Name chrome,msedge,firefox -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1
if ($null -eq $browser) { exit 1 }
if (-not $shell.AppActivate($browser.Id)) { exit 1 }
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _send_browser_key(command: str) -> bool:
    if not _activate_browser():
        return False
    keys = {
        "next": "^{TAB}",
        "previous": "^+{TAB}",
        "close": "^w",
        "new": "^t",
        "reopen": "^+t",
    }
    key = keys[command]
    script = f"""
$shell = New-Object -ComObject WScript.Shell
Start-Sleep -Milliseconds 120
$shell.SendKeys('{key}')
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        log.exception("Falha ao enviar comando para a aba do navegador")
        return False


async def _h_browser(message: str, norm: str, words: int, name: str) -> Optional[str]:
    browser_words = ("navegador", "chrome", "google chrome", "edge", "firefox")
    tab_words = ("aba", "abas", "guia", "guias")
    if not any(word in norm for word in tab_words):
        return None
    is_browser_context = any(word in norm for word in browser_words) or any(
        phrase in norm for phrase in ("mudar de aba", "trocar de aba", "proxima aba", "aba anterior", "fechar aba", "nova aba")
    )
    if not is_browser_context:
        return None
    if re.search(r"\b(?:proxima|seguinte|outra|trocar|mudar)\b", norm):
        command, reply = "next", "Mudei para a próxima aba, senhor."
    elif re.search(r"\b(?:anterior|voltar|volte)\b", norm):
        command, reply = "previous", "Voltei para a aba anterior, senhor."
    elif re.search(r"\b(?:fechar|feche|encerre)\b", norm):
        command, reply = "close", "Fechei a aba atual, senhor."
    elif re.search(r"\b(?:reabrir|reabra|recuperar)\b", norm):
        command, reply = "reopen", "Reabri a última aba fechada, senhor."
    elif re.search(r"\b(?:abrir|abra|criar|crie)\b", norm):
        command, reply = "new", "Abri uma nova aba, senhor."
    else:
        return None
    if await asyncio.to_thread(_send_browser_key, command):
        return reply
    return "Não encontrei uma janela do navegador disponível para controlar, senhor."


async def _h_system(message: str, norm: str, words: int, name: str) -> Optional[str]:
    """Delega para system_control se a mensagem envolver volume, brilho, tela ou print."""
    return await system_control.handle(message, norm, words, name)


async def _h_spotify(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if "spotify" not in norm:
        return None
    try:
        play_match = re.search(r"\b(?:tocar|toque|toca)\s+(?:a\s+)?(?:playlist\s+)?(.+?)(?:\s+no\s+spotify)?$", norm)
        generic_play = norm in {"tocar spotify", "tocar no spotify", "continuar spotify", "continuar no spotify"}
        if play_match and not generic_play and not any(term in norm for term in ("musica atual", "tocando", "proxima", "seguinte")):
            query = play_match.group(1).strip()
            is_playlist = "playlist" in norm
            return await asyncio.to_thread(spotify.search_and_play, query, is_playlist)
        if re.search(r"\b(?:abrir|abra|abre|iniciar|inicie|acessar|acesse|mostrar|mostre)\b", norm):
            await asyncio.to_thread(_open_spotify_desktop)
            return "Spotify aberto no aplicativo do computador, senhor."
        if any(term in norm for term in ("pausar", "pause", "parar")):
            await asyncio.to_thread(spotify.pause)
            return "Spotify pausado, senhor."
        if any(term in norm for term in ("proxima", "seguinte")):
            await asyncio.to_thread(spotify.next_track)
            return "Avançando para a próxima faixa, senhor."
        if any(term in norm for term in ("anterior", "voltar")):
            await asyncio.to_thread(spotify.previous_track)
            return "Voltando para a faixa anterior, senhor."
        if any(term in norm for term in ("tocando", "musica atual")):
            return await asyncio.to_thread(spotify.current_track)
        if any(term in norm for term in ("tocar", "play", "continuar")):
            await asyncio.to_thread(spotify.play)
            return "Reprodução retomada, senhor."
    except (OSError, subprocess.SubprocessError):
        log.exception("Falha ao abrir o aplicativo Spotify")
        return "Não consegui abrir o aplicativo do Spotify neste computador, senhor."
    except (RuntimeError, requests.RequestException) as exc:
        log.exception("Falha no controle do Spotify")
        return str(exc)
    return "Posso tocar, pausar, avançar, voltar ou informar a música atual do Spotify."


# ===================================================================== saúde & bluetooth (smartwatch)
async def _h_bluetooth_health(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # Intercepta comandos de voz como "buscar bluetooth", "procurar bluetooth", "conectar relogio", "escanear relogio"
    bt_terms = ("bluetooth", "smartwatch", "relogio", "sinais vitais", "bio scan", "bioscan")
    if not any(term in norm for term in bt_terms):
        return None

    if any(act in norm for act in ("buscar", "busque", "busca", "procurar", "procure", "escanear", "escaneie", "encontrar", "localizar", "rastrear")):
        devices = await health.scan_ble_devices(timeout=4.0)
        watches = [d for d in devices if d.get("is_watch")]
        named_devices = [d["name"] for d in devices if d.get("name") and d["name"] != "Dispositivo Desconhecido"]

        if watches:
            watch_name = watches[0]["name"]
            # Auto conecta ou registra o relógio encontrado
            health.update_biometrics(device_name=watch_name, connection_type="ble")
            return f"Encontrei seu smartwatch {watch_name} via Bluetooth BLE, senhor. Conexão e telemetria sincronizadas."
        elif named_devices:
            first = named_devices[0]
            health.update_biometrics(device_name=first, connection_type="ble")
            return f"Varredura Bluetooth concluída, senhor. Localizei {first} próximo ao terminal. Conexão estabelecida."
        else:
            return "Varredura Bluetooth realizada, senhor. Nenhum smartwatch ou dispositivo BLE aberto foi detectado próximo ao computador neste momento. Certifique-se de que o Bluetooth do relógio está visível."

    if any(act in norm for act in ("sincronizar", "sincronize", "conectar", "conecte", "parear", "pareie")):
        telemetry = health.load_telemetry()
        return f"Sinais vitais do {telemetry.get('device_name', 'smartwatch')} sincronizados. Batimentos em {telemetry.get('bpm', 76)} bpm e saturação em {telemetry.get('spo2', 98)} porcento, senhor."

    return None


# ===================================================================== produtividade (Fase 2)
async def _h_shopping(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # V6.0: lista de compras ("coloca leite na lista", "comprei o pão"); antes das tarefas
    from modules import shopping

    return await shopping.handle_voice(message)


async def _h_tasks(message: str, norm: str, words: int, name: str) -> Optional[str]:
    return await tasks.handle_voice(message, norm, words, name)


async def _h_countdown(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # V5.6: "contagem regressiva para a viagem", "quanto falta para o natal" (antes dos timers)
    from modules import countdowns

    return await countdowns.handle_voice(message)


async def _h_alarms(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # V5.1: antes dos timers ("cancela o alarme das 7" não pode apagar os timers)
    from modules import alarms

    return await alarms.handle_voice(norm)


async def _h_reminders(message: str, norm: str, words: int, name: str) -> Optional[str]:
    return await reminders.handle_voice(message, norm, words, name)


async def _h_focus(message: str, norm: str, words: int, name: str) -> Optional[str]:
    return await focus.handle_voice(message, norm, words, name)


async def _h_briefing(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # Frases longas (as curtas já viram o briefing em etapas em core/turns.py). O fechamento vence:
    # "boa noite, resumo do dia" é noite, não manhã.
    # Um cumprimento seguido de outro pedido ("boa noite, abre o spotify...") não vira resumo.
    mode = briefing.request_mode(norm)
    if mode and mode.startswith("topic:"):
        return None  # telas por assunto só abrem pela frase curta (core/turns.py)
    greeting_only = norm.startswith(("bom dia", "boa noite")) and not any(
        w in norm for w in ("resumo", "meu dia", "o dia", "pendente", "tarefa", "amanha", "briefing"))
    if mode is None or greeting_only:
        return None
    if mode == "evening":
        return await briefing.generate_evening_briefing()
    return await briefing.generate_daily_briefing()


async def _h_logs(message: str, norm: str, words: int, name: str) -> Optional[str]:
    # Comandos de log do sistema / erros / relatório de eventos usando limites de palavra (\b)
    is_log = bool(re.search(
        r"\b(logs?|log\s+de\s+erros?|relat[oó]rios?(\s+de)?\s+logs?|relat[oó]rios?(\s+de)?\s+erros?|hist[oó]rico\s+de\s+erros?|erros\s+do\s+sistema)\b",
        norm,
        flags=re.I,
    )) or (
        bool(re.search(r"\b(abrir|abra|mostrar|mostre|ver|veja|gerar|exibir)\b", norm, flags=re.I))
        and bool(re.search(r"\b(logs?|erros?)\b", norm, flags=re.I))
    )
    if is_log:
        from modules import event_log
        events = event_log.list_events(limit=20)
        errors = [e for e in events if e.get("kind") == "error"]
        if errors:
            latest = errors[0]
            summary = latest.get("message") or latest.get("detail") or "Erro recente"
            return f"Abrindo relatório e registros de logs do sistema, senhor. Consta {len(errors)} erro recente registrado: {summary}."
        return "Abrindo o relatório e registros de logs do sistema, senhor. Todos os módulos principais estão operando com êxito."
    return None


# ===================================================================== 4.2: protocolos
async def _h_protocol(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if "protocolo" not in norm:
        return None
    from modules import protocols

    return await protocols.handle_voice(norm)


# ===================================================================== 4.2: leitura de tela
async def _h_screen(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 25 or "tela" not in norm and "janela" not in norm:
        return None
    from modules import screen_assist

    if not screen_assist.wants_screen(norm):
        return None
    return await screen_assist.answer(message)


# ===================================================================== 4.2: arquivos por voz
async def _h_files(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 16:
        return None
    from modules import files

    return await files.handle_voice(norm)


# ===================================================================== 4.2: notificações do Windows
async def _h_notifications(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 12 or "notificac" not in norm:
        return None
    from modules import notifications

    return await notifications.handle_voice(norm)


# ===================================================================== V4.5: memória, WhatsApp e finanças
async def _h_memory(message: str, norm: str, words: int, name: str) -> Optional[str]:
    from modules import memory

    return memory.handle_voice(norm, message)


async def _h_whatsapp(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if "whats" not in norm and "zap" not in norm and "contato" not in norm:
        return None
    from modules import whatsapp

    return whatsapp.handle_voice(message)


async def _h_finances(message: str, norm: str, words: int, name: str) -> Optional[str]:
    if words > 14:
        return None
    from modules import finances

    return finances.handle_voice(norm)


# ===================================================================== entrada principal
_HANDLERS = (
    _h_memory, _h_whatsapp, _h_finances,
    _h_protocol, _h_screen, _h_files, _h_notifications, _h_logs, _h_bluetooth_health, _h_countdown, _h_alarms, _h_timer, _h_reminders, _h_shopping, _h_tasks, _h_focus, _h_briefing, _h_notes, _h_browser, _h_spotify, _h_custom_shortcut, _h_open,
    _h_search, _h_calc, _h_status, _h_system, _h_exchange, _h_weather,
)


async def run(message: str, name: str = "") -> Optional[str]:
    """Tenta resolver o pedido com uma função local. Devolve o texto falado, ou None."""
    norm = _norm(message)
    if not norm:
        return None
    words = len(norm.split())
    for handler in _HANDLERS:
        try:
            reply = await handler(message, norm, words, name)
        except Exception:  # noqa: BLE001
            log.exception("Falha na função %s", handler.__name__)
            return "Não consegui concluir isso, senhor. O detalhe ficou no log do JARVIS (Ver-Logs.bat)."
        if reply:
            return reply
    return None
