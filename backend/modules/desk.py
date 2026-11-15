"""V8.0: MODO DESK (ideia 6 do documento de atualização): o JARVIS como app de assistente pessoal no PC.

Aqui fica o que é novo no Modo Desk (o resto reaproveita o JARVIS de sempre):
- aparência: avatar robô (cores, expressão, acessório), cor principal do app e a ilha do JARVIS.exe;
- Nível e XP: o JARVIS ganha experiência conforme é usado;
- Hábitos: marcar o dia, sequência de dias e lembrete;
- Copiados: histórico do Ctrl+C no PC (só no PC; não guarda o que parece senha, cartão ou código);
- Memória em mapa: as memórias agrupadas por assunto.
"""
from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
import uuid
from datetime import date, datetime, timedelta

from config import settings

_PATH = settings.DATA_DIR / "desk.json"
_CLIP_PATH = settings.DATA_DIR / "copiados.json"
_lock = threading.RLock()

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
EXPRESSIONS = ("feliz", "pensando", "falando", "ouvindo", "dormindo", "surpreso", "piscando")
ACCESSORIES = ("nenhum", "fone", "oculos", "gorro", "coroa")
ISLAND_SIZES = ("pequena", "media", "grande")
DEFAULT = {
    "avatar": {"corpo": "#e8f4ff", "visor": "#0b1220", "olhos": "#22d3ee", "expressao": "feliz", "acessorio": "nenhum"},
    "cor": "#22d3ee",
    "ilha": {"ligada": True, "tamanho": "media", "atalho": "PageDown"},
    "xp": {"total": 0, "hoje": {}, "eventos": []},
    "habitos": [],
}
# quanto XP vale cada coisa (por dia, cada tipo tem um teto para não virar "farm")
XP = {"conversa": (2, 40), "tarefa": (10, 100), "habito": (15, 150), "rotina": (8, 40), "lembrete": (3, 30), "memoria": (5, 25)}
LEVEL_BASE = 100  # nível n precisa de 100 × n XP a mais que o anterior
MAX_HABITS = 20
MAX_CLIPS = 50


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    out = json.loads(json.dumps(DEFAULT))
    for k, v in (data if isinstance(data, dict) else {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k].update(v)
        elif k in out:
            out[k] = v
    return out


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- aparência
def config() -> dict:
    d = _load()
    return {"avatar": d["avatar"], "cor": d["cor"], "ilha": d["ilha"], "nivel": level_info(d["xp"]["total"])}


def update_config(patch: dict) -> dict:
    """Muda só o que veio e só com valores válidos (o resto é ignorado)."""
    with _lock:
        d = _load()
        av = patch.get("avatar") if isinstance(patch.get("avatar"), dict) else {}
        for k in ("corpo", "visor", "olhos"):
            if isinstance(av.get(k), str) and HEX.match(av[k]):
                d["avatar"][k] = av[k].lower()
        if av.get("expressao") in EXPRESSIONS:
            d["avatar"]["expressao"] = av["expressao"]
        if av.get("acessorio") in ACCESSORIES:
            d["avatar"]["acessorio"] = av["acessorio"]
        if isinstance(patch.get("cor"), str) and HEX.match(patch["cor"]):
            d["cor"] = patch["cor"].lower()
        ilha = patch.get("ilha") if isinstance(patch.get("ilha"), dict) else {}
        if isinstance(ilha.get("ligada"), bool):
            d["ilha"]["ligada"] = ilha["ligada"]
        if ilha.get("tamanho") in ISLAND_SIZES:
            d["ilha"]["tamanho"] = ilha["tamanho"]
        if isinstance(ilha.get("atalho"), str) and re.fullmatch(r"[A-Za-z0-9+]{1,24}", ilha["atalho"]):
            d["ilha"]["atalho"] = ilha["atalho"]
        _save(d)
    return config()


# --------------------------------------------------------------------------- nível e XP
def level_info(total: int) -> dict:
    """Nível 1 começa no 0; o nível n+1 precisa de 100·n XP além do nível n (100, 200, 300…)."""
    total = max(0, int(total or 0))
    level, need, acc = 1, LEVEL_BASE, 0
    while total >= acc + need:
        acc += need
        level += 1
        need = LEVEL_BASE * level
    return {"nivel": level, "xp": total, "no_nivel": total - acc, "para_subir": need, "pct": round((total - acc) / need * 100)}


def add_xp(kind: str, today: date | None = None) -> dict | None:
    """Soma XP pela ação; devolve {"ganhou", "subiu", ...} ou None (tipo desconhecido ou teto do dia)."""
    if kind not in XP:
        return None
    pts, cap = XP[kind]
    today = today or date.today()
    key = today.isoformat()
    with _lock:
        d = _load()
        x = d["xp"]
        if x.get("hoje", {}).get("_dia") != key:
            x["hoje"] = {"_dia": key}
        got = x["hoje"].get(kind, 0)
        if got >= cap:
            return None
        gain = min(pts, cap - got)
        before = level_info(x["total"])["nivel"]
        x["total"] = int(x.get("total", 0)) + gain
        x["hoje"][kind] = got + gain
        x["eventos"] = ([{"tipo": kind, "xp": gain, "em": datetime.now().isoformat(timespec="seconds")}] + x.get("eventos", []))[:30]
        _save(d)
        info = level_info(x["total"])
        return {"ganhou": gain, "subiu": info["nivel"] > before, **info}


def xp_quietly(kind: str) -> None:
    """XP sem atrapalhar quem chamou (tarefa feita, lembrete criado, conversa…)."""
    try:
        add_xp(kind)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- hábitos
def _streak(done: dict, today: date) -> int:
    n = 0
    day = today if done.get(today.isoformat()) else today - timedelta(days=1)
    while done.get(day.isoformat()):
        n += 1
        day -= timedelta(days=1)
    return n


def _habit_view(h: dict, today: date) -> dict:
    done = h.get("feito") or {}
    week = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    return {"id": h["id"], "nome": h["nome"], "icone": h.get("icone") or "✓", "lembrete": h.get("lembrete") or "",
            "hoje": bool(done.get(today.isoformat())), "sequencia": _streak(done, today),
            "semana": [bool(done.get(d)) for d in week], "total": sum(1 for v in done.values() if v)}


def habits(today: date | None = None) -> dict:
    today = today or date.today()
    items = [_habit_view(h, today) for h in _load()["habitos"]]
    return {"itens": items, "feitos_hoje": sum(1 for h in items if h["hoje"]), "total": len(items)}


def habit_add(nome: str, icone: str = "", lembrete: str = "") -> dict:
    nome = re.sub(r"\s+", " ", str(nome or "")).strip()[:40]
    if not nome:
        raise ValueError("Diga o nome do hábito.")
    if lembrete and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", lembrete):
        raise ValueError("Horário do lembrete inválido (use HH:MM).")
    with _lock:
        d = _load()
        if any(_norm(h["nome"]) == _norm(nome) for h in d["habitos"]):
            raise ValueError("Esse hábito já existe.")
        if len(d["habitos"]) >= MAX_HABITS:
            raise ValueError(f"No máximo {MAX_HABITS} hábitos.")
        d["habitos"].append({"id": uuid.uuid4().hex[:8], "nome": nome, "icone": str(icone or "")[:4], "lembrete": lembrete, "feito": {}})
        _save(d)
    return habits()


def _find(d: dict, ref: str) -> dict | None:
    r = _norm(ref)
    return next((h for h in d["habitos"] if h["id"] == ref), None) or next(
        (h for h in d["habitos"] if r and (r in _norm(h["nome"]) or _norm(h["nome"]) in r)), None)


def habit_toggle(ref: str, done: bool | None = None, day: date | None = None) -> dict:
    day = day or date.today()
    with _lock:
        d = _load()
        h = _find(d, ref)
        if not h:
            raise ValueError("Não achei esse hábito.")
        key = day.isoformat()
        now = (not h["feito"].get(key)) if done is None else bool(done)
        if now:
            h["feito"][key] = True
        else:
            h["feito"].pop(key, None)
        # guarda só ~1 ano de histórico
        cut = (day - timedelta(days=370)).isoformat()
        h["feito"] = {k: v for k, v in h["feito"].items() if k >= cut}
        _save(d)
    if now:
        add_xp("habito", day)
    return {**habits(day), "habito": _habit_view(h, day)}


def habit_remove(ref: str) -> dict:
    with _lock:
        d = _load()
        h = _find(d, ref)
        if not h:
            raise ValueError("Não achei esse hábito.")
        d["habitos"] = [x for x in d["habitos"] if x["id"] != h["id"]]
        _save(d)
    return habits()


def habit_reminders(now: datetime | None = None) -> list[str]:
    """Hábitos com lembrete AGORA e ainda não feitos hoje."""
    now = now or datetime.now()
    hm = now.strftime("%H:%M")
    today = now.date().isoformat()
    return [f"Lembrete do hábito: {h['nome']}." for h in _load()["habitos"]
            if h.get("lembrete") == hm and not (h.get("feito") or {}).get(today)]


def handle_voice(norm: str) -> str | None:
    """"jarvis, marquei o treino de hoje" / "fiz o hábito de leitura" / "como estão meus hábitos?"."""
    d = _load()
    if not d["habitos"]:
        return None
    if re.search(r"\b(meus habitos|habitos de hoje|como (estao|vao) (os |meus )?habitos)\b", norm):
        h = habits()
        falta = [x["nome"] for x in h["itens"] if not x["hoje"]]
        return f"Hoje você fez {h['feitos_hoje']} de {h['total']} hábitos." + (f" Faltam: {', '.join(falta)}." if falta else " Todos feitos, senhor!")
    if not re.search(r"\b(marquei|marca|marcar|fiz|conclui|cumpri)\b", norm):
        return None
    stems = {w[:5] for w in norm.split() if len(w) > 3}
    for h in d["habitos"]:
        hn = _norm(h["nome"])
        # "treino" casa com "Treinar", "leitura" com "Leitura de 10 páginas" (as 5 primeiras letras)
        if hn and (hn in norm or any(w[:5] in stems for w in hn.split() if len(w) > 3)):
            r = habit_toggle(h["id"], True)
            s = r["habito"]["sequencia"]
            return f"Hábito marcado: {h['nome']}. Sequência de {s} {'dia' if s == 1 else 'dias'}, senhor."
    return None


# --------------------------------------------------------------------------- copiados
_SECRET = [
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),  # cartão
    re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^\w\s]).{8,40}$"),  # cara de senha (curta, mista, sem espaço)
    re.compile(r"\b(sk|pk|rk|ghp|gho|xox[abp]|AIza)[-_A-Za-z0-9]{16,}"),  # chaves de API
    re.compile(r"^[A-Za-z0-9+/=_-]{32,}$"),  # tokens longos
    re.compile(r"\b(senha|password|pin|cvv|token)\b\s*[:=]", re.I),
    re.compile(r"^\d{4,8}$"),  # códigos de verificação
]


def looks_secret(text: str) -> bool:
    t = str(text or "").strip()
    return any(p.search(t) for p in _SECRET)


def _clips_load() -> dict:
    try:
        data = json.loads(_CLIP_PATH.read_text(encoding="utf-8")) if _CLIP_PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    return {"pausado": bool(data.get("pausado")), "itens": [i for i in data.get("itens") or [] if isinstance(i, dict) and i.get("texto")]}


def _clips_save(data: dict) -> None:
    _CLIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CLIP_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def clips() -> dict:
    return _clips_load()


def clip_add(text: str) -> bool:
    """Guarda um texto copiado (se não estiver pausado, não for repetido e não parecer segredo)."""
    t = str(text or "").replace("\r\n", "\n").strip()
    if not t or len(t) > 5000 or looks_secret(t):
        return False
    with _lock:
        data = _clips_load()
        if data["pausado"]:
            return False
        if data["itens"] and data["itens"][0]["texto"] == t:
            return False
        data["itens"] = [i for i in data["itens"] if i["texto"] != t]
        data["itens"].insert(0, {"id": uuid.uuid4().hex[:8], "texto": t, "em": datetime.now().strftime("%Y-%m-%d %H:%M")})
        data["itens"] = data["itens"][:MAX_CLIPS]
        _clips_save(data)
        return True


def clip_remove(item_id: str | None = None) -> dict:
    with _lock:
        data = _clips_load()
        data["itens"] = [] if item_id is None else [i for i in data["itens"] if i["id"] != item_id]
        _clips_save(data)
        return data


def clip_pause(paused: bool) -> dict:
    with _lock:
        data = _clips_load()
        data["pausado"] = bool(paused)
        _clips_save(data)
        return data


def read_clipboard() -> str:
    """Texto da área de transferência do Windows (ctypes, sem bibliotecas extras). Fora do Windows: ""."""
    import sys

    if sys.platform != "win32":
        return ""
    import ctypes
    from ctypes import wintypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        try:
            return ctypes.wstring_at(ptr) if ptr else ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


async def clipboard_loop(interval: float = 1.5) -> None:
    """Vigia a área de transferência do PC (só Windows) e guarda o que for copiado."""
    import asyncio
    import logging
    import sys

    if sys.platform != "win32":
        return
    log = logging.getLogger("jarvis.desk")
    last = None
    while True:
        try:
            text = await asyncio.to_thread(read_clipboard)
            if text and text != last:
                last = text
                clip_add(text)
        except Exception:  # noqa: BLE001 - a área de transferência ocupada por outro programa não para o JARVIS
            log.debug("Copiados: leitura falhou", exc_info=True)
        await asyncio.sleep(interval)


async def habits_loop(interval: float = 60) -> None:
    """Lembretes dos hábitos no horário marcado (voz no PC e notificação no celular)."""
    import asyncio
    import logging

    from core import speech

    log = logging.getLogger("jarvis.desk")
    await asyncio.sleep(20)
    sent = set()
    while True:
        try:
            now = datetime.now()
            key = now.strftime("%Y-%m-%d %H:%M")
            if key not in sent:
                sent = {k for k in sent if k.startswith(now.strftime("%Y-%m-%d"))}
                sent.add(key)
                for text in habit_reminders(now):
                    await speech.announce(text)
        except Exception:  # noqa: BLE001
            log.exception("Lembretes dos hábitos falharam")
        await asyncio.sleep(interval - (time.time() % interval))


# --------------------------------------------------------------------------- memória em mapa
TOPICS = [
    ("Pessoas", "👥", r"\b(esposa|marido|namorad[ao]|filh[ao]s?|mae|pai|irma[o]?|amig[ao]s?|chama|chamad[ao]|aniversario|familia|sogr[ao]|vo|avo)\b"),
    ("Gostos", "❤", r"\b(gosto|gosta|prefiro|prefere|adoro|ama|odeio|favorit[ao]|time|torce|musica|banda|comida|cor)\b"),
    ("Casa", "🏠", r"\b(casa|apartamento|endereco|mora|cidade|bairro|quarto|cozinha|carro|pet|cachorro|gato)\b"),
    ("Trabalho", "💼", r"\b(trabalho|trabalha|empresa|emprego|cliente|reuniao|projeto|chefe|escritorio|curso|faculdade)\b"),
    ("Saúde", "🩺", r"\b(saude|remedio|medico|alergia|academia|treino|dieta|peso|dormir|sono|pressao)\b"),
    ("Dinheiro", "💰", r"\b(dinheiro|divida|salario|conta|banco|cartao|parcela|investimento|gasto)\b"),
]


def memory_map() -> dict:
    """As memórias do JARVIS agrupadas por assunto: um nó central, um nó por assunto e uma folha por memória."""
    from modules import memory

    mem = memory.get_memory()
    items = [{"texto": f.get("text", ""), "tipo": "fato"} for f in mem.get("facts", []) if f.get("text")]
    items += [{"texto": f.get("text", ""), "tipo": "rotina"} for f in mem.get("routine", []) if f.get("text")]
    items += [{"texto": f"{k}: {v}", "tipo": "preferencia"} for k, v in (mem.get("preferences") or {}).items() if v]
    groups: dict[str, list] = {}
    for it in items:
        n = _norm(it["texto"])
        topic = next((t for t in TOPICS if re.search(t[2], n)), None)
        name = topic[0] if topic else ("Rotina" if it["tipo"] == "rotina" else "Outras coisas")
        groups.setdefault(name, []).append(it)
    icons = {t[0]: t[1] for t in TOPICS} | {"Rotina": "⏰", "Outras coisas": "✦"}
    nodes = [{"id": "eu", "rotulo": "Você", "tipo": "centro"}]
    links = []
    for name, its in groups.items():
        gid = f"g:{name}"
        nodes.append({"id": gid, "rotulo": name, "icone": icons.get(name, "✦"), "tipo": "assunto", "qtd": len(its)})
        links.append({"de": "eu", "para": gid})
        for i, it in enumerate(its[:40]):
            mid = f"m:{name}:{i}"
            nodes.append({"id": mid, "rotulo": it["texto"][:120], "tipo": "memoria", "origem": it["tipo"]})
            links.append({"de": gid, "para": mid})
    return {"nos": nodes, "ligacoes": links, "total": len(items)}


# --------------------------------------------------------------------------- resumo para a nuvem
def cloud_summary() -> dict:
    """Fora de casa: aparência, nível e hábitos (os Copiados nunca saem do PC)."""
    d = _load()
    return {"avatar": d["avatar"], "cor": d["cor"], "nivel": level_info(d["xp"]["total"]), "habitos": habits()["itens"]}
