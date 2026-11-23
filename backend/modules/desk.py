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
EXPRESSIONS = ("feliz", "pensando", "falando", "ouvindo", "dormindo", "surpreso", "piscando",
               # V8.2 (ideia 8): mais expressões
               "repouso", "rindo", "carinho", "descolado", "bravo", "chorando", "conseguiu")
ACCESSORIES = ("nenhum", "fone", "oculos", "gorro", "coroa")
ISLAND_SIZES = ("pequena", "media", "grande")
# V8.1: GUARDA-ROUPA do robô (ideia 7). Cada item: (id, None = liberado | {"nivel": n} | {"ofensiva": dias}).
WARDROBE: dict[str, list[tuple[str, dict | None]]] = {
    "chapeu": [("nenhum", None), ("gorro", None), ("bone", None), ("fone", None), ("cartola", {"nivel": 3}),
               ("gatinho", {"nivel": 5}), ("bruxa", {"ofensiva": 7}), ("headset", {"nivel": 8}), ("coroa", {"nivel": 10}),
               # V8.2 (ideia 8)
               ("aureola", None), ("chifrinhos", None), ("festa", None), ("flor", None), ("bone_time", None)],
    "rosto": [("nenhum", None), ("oculos", None), ("laco", None), ("bigode", {"nivel": 2}), ("oculos_escuros", {"nivel": 4})],
    "roupa": [("nenhuma", None), ("cachecol", None), ("gravata", {"nivel": 2}), ("camisa", {"nivel": 3}),
              ("capa", {"ofensiva": 30}), ("armadura", {"nivel": 15})],
    "olhos_forma": [("reator", None), ("coracao", {"nivel": 2}), ("estrela", {"ofensiva": 3}), ("pixel", {"nivel": 6})],
    "efeito": [("nenhum", None), ("brilho", {"nivel": 3}), ("neve", {"nivel": 5}), ("faiscas", {"ofensiva": 14})],
}
WARDROBE_DEFAULT = {"chapeu": "nenhum", "rosto": "nenhum", "roupa": "nenhuma", "olhos_forma": "reator", "efeito": "nenhum"}
OLD_ACCESSORY = {"fone": ("chapeu", "fone"), "gorro": ("chapeu", "gorro"), "coroa": ("chapeu", "coroa"), "oculos": ("rosto", "oculos")}
DEFAULT = {
    "avatar": {"corpo": "#e8f4ff", "visor": "#0b1220", "olhos": "#22d3ee", "expressao": "feliz", "acessorio": "nenhum",
               **WARDROBE_DEFAULT, "temas": True, "antena": True, "olhos_seguem": True, "olhos_vel": 1.0,
               "piscar": True, "brincadeiras": True},  # V8.4.0 (ideia 10)
    "cor": "#22d3ee",
    # V8.5.0: painel (tamanho da ilha aberta) e zoom (do conteúdo dela)
    "ilha": {"ligada": True, "tamanho": "media", "atalho": "PageDown", "posicao": 0.5, "painel": "medio", "zoom": 0.9,
             "ocultar": True},  # V8.7.0: escondida no topo, desce quando o mouse chega lá
    # V8.5.0: atualiza sozinho quando o JARVIS está parado; V8.11: e ao abrir a central (se houver versão nova)
    "atualizacao": {"automatica": True, "ao_abrir": True},
    # V8.4.0 (ideia 10): modo leve: "auto" (liga sozinho no notebook na bateria), "sim" ou "nao"
    "desempenho": {"leve": "auto"},
    "xp": {"total": 0, "hoje": {}, "eventos": []},
    "habitos": [],
}
# quanto XP vale cada coisa (por dia, cada tipo tem um teto para não virar "farm")
XP = {"conversa": (2, 40), "tarefa": (10, 100), "habito": (15, 150), "rotina": (8, 40), "lembrete": (3, 30), "memoria": (5, 25)}
LITE_MODES = ("auto", "sim", "nao")  # V8.4.0
PANEL_SIZES = ("compacto", "medio", "grande")  # V8.5.0
ZOOM_RANGE = (0.7, 1.4)
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
    return _migrate(out)


def _migrate(out: dict) -> dict:
    """8.0 tinha um só "acessorio": vira chapéu ou rosto do guarda-roupa (uma vez)."""
    av = out["avatar"]
    old = av.get("acessorio")
    if old in OLD_ACCESSORY:
        slot, item = OLD_ACCESSORY[old]
        if av.get(slot) in (None, WARDROBE_DEFAULT[slot]):
            av[slot] = item
        av["acessorio"] = "nenhum"
    return out


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- aparência
def _streak_record() -> int:
    try:
        from modules import desk_missions

        return desk_missions.streak_record()
    except Exception:  # noqa: BLE001
        return 0


def unlock_status(level: int, record: int) -> dict:
    """{slot: [{"id", "liberado", "precisa"}]} (precisa = "Nível 5" / "7 dias de ofensiva")."""
    out = {}
    for slot, items in WARDROBE.items():
        out[slot] = []
        for item, req in items:
            ok = req is None or level >= req.get("nivel", 0) and record >= req.get("ofensiva", 0)
            need = "" if req is None else f"Nível {req['nivel']}" if "nivel" in req else f"{req['ofensiva']} dias de ofensiva"
            out[slot].append({"id": item, "liberado": bool(ok), "precisa": need})
    return out


def unlocked_ids(level: int, record: int) -> set[str]:
    return {f"{slot}:{i['id']}" for slot, items in unlock_status(level, record).items() for i in items if i["liberado"]}


def _easter(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def game_day(today: date) -> bool:
    """Dia de jogo do time (pelo cache do Modo Torcedor, sem buscar na internet)."""
    try:
        from modules import sports_provider

        cache = sports_provider.load_fan_cache()
        for m in sports_provider._matches(cache, "palmeiras"):
            dt = sports_provider._parse_dt(m.get("date"))
            if dt and dt.date() == today and m.get("status") != "postponed":
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def season_theme(today: date | None = None) -> dict | None:
    """Tema das datas (só por cima do visual escolhido): Natal, Halloween, Carnaval e dia de jogo."""
    today = today or date.today()
    if (today.month == 12 and today.day <= 26):
        return {"nome": "Natal", "chapeu": "gorro", "efeito": "neve"}
    if today.month == 10 and today.day >= 25:
        return {"nome": "Halloween", "chapeu": "abobora", "efeito": "brilho"}
    carnaval = _easter(today.year) - timedelta(days=47)  # terça de Carnaval
    if carnaval - timedelta(days=3) <= today <= carnaval + timedelta(days=1):
        return {"nome": "Carnaval", "efeito": "confete"}
    if game_day(today):
        return {"nome": "Dia de jogo", "roupa": "camisa"}
    return None


def config() -> dict:
    d = _load()
    lv = level_info(d["xp"]["total"])
    record = _streak_record()
    return {"avatar": d["avatar"], "cor": d["cor"], "ilha": d["ilha"], "desempenho": d["desempenho"], "atualizacao": d["atualizacao"], "nivel": lv,
            "tema": season_theme() if d["avatar"].get("temas", True) else None,
            "guarda_roupa": unlock_status(lv["nivel"], record), "ofensiva_recorde": record}


def update_config(patch: dict) -> dict:
    """Muda só o que veio e só com valores válidos (o resto é ignorado). Item bloqueado: ValueError."""
    with _lock:
        d = _load()
        av = patch.get("avatar") if isinstance(patch.get("avatar"), dict) else {}
        for k in ("corpo", "visor", "olhos"):
            if isinstance(av.get(k), str) and HEX.match(av[k]):
                d["avatar"][k] = av[k].lower()
        if av.get("expressao") in EXPRESSIONS:
            d["avatar"]["expressao"] = av["expressao"]
        if av.get("acessorio") in OLD_ACCESSORY:  # compatibilidade com o 8.0
            slot, item = OLD_ACCESSORY[av["acessorio"]]
            av.setdefault(slot, item)
        status = unlock_status(level_info(d["xp"]["total"])["nivel"], _streak_record())
        for slot in WARDROBE:
            want = av.get(slot)
            if want is None:
                continue
            item = next((i for i in status[slot] if i["id"] == want), None)
            if not item:
                continue
            if not item["liberado"]:
                raise ValueError(f"Bloqueado: libera com {item['precisa']}.")
            d["avatar"][slot] = want
        if isinstance(av.get("temas"), bool):
            d["avatar"]["temas"] = av["temas"]
        for k in ("antena", "olhos_seguem", "piscar", "brincadeiras"):  # V8.2 / V8.4.0
            if isinstance(av.get(k), bool):
                d["avatar"][k] = av[k]
        if isinstance(av.get("olhos_vel"), (int, float)) and not isinstance(av.get("olhos_vel"), bool):
            d["avatar"]["olhos_vel"] = round(min(2.0, max(0.25, float(av["olhos_vel"]))), 2)
        des = patch.get("desempenho") if isinstance(patch.get("desempenho"), dict) else {}
        if des.get("leve") in LITE_MODES:
            d["desempenho"]["leve"] = des["leve"]
        if isinstance(patch.get("cor"), str) and HEX.match(patch["cor"]):
            d["cor"] = patch["cor"].lower()
        ilha = patch.get("ilha") if isinstance(patch.get("ilha"), dict) else {}
        if isinstance(ilha.get("ligada"), bool):
            d["ilha"]["ligada"] = ilha["ligada"]
        if ilha.get("tamanho") in ISLAND_SIZES:
            d["ilha"]["tamanho"] = ilha["tamanho"]
        if isinstance(ilha.get("atalho"), str) and re.fullmatch(r"[A-Za-z0-9+]{1,24}", ilha["atalho"]):
            d["ilha"]["atalho"] = ilha["atalho"]
        pos = ilha.get("posicao")  # V8.4.1: onde a ilha fica no topo (0..1 da largura da tela; arrastada no app)
        if isinstance(pos, (int, float)) and not isinstance(pos, bool):
            d["ilha"]["posicao"] = round(min(1.0, max(0.0, float(pos))), 4)
        if isinstance(ilha.get("ocultar"), bool):
            d["ilha"]["ocultar"] = ilha["ocultar"]
        if ilha.get("painel") in PANEL_SIZES:
            d["ilha"]["painel"] = ilha["painel"]
        z = ilha.get("zoom")
        if isinstance(z, (int, float)) and not isinstance(z, bool):
            d["ilha"]["zoom"] = round(min(ZOOM_RANGE[1], max(ZOOM_RANGE[0], float(z))), 2)
        upd = patch.get("atualizacao") if isinstance(patch.get("atualizacao"), dict) else {}
        if isinstance(upd.get("automatica"), bool):
            d["atualizacao"]["automatica"] = upd["automatica"]
        if isinstance(upd.get("ao_abrir"), bool):
            d["atualizacao"]["ao_abrir"] = upd["ao_abrir"]
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
    try:  # V8.1: as missões de "usar o JARVIS" contam mesmo depois do teto de XP do dia
        from modules import desk_missions

        desk_missions.track(kind, today)
    except Exception:  # noqa: BLE001
        pass
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


def add_xp_raw(points: int, reason: str) -> dict:
    """XP de missão (sem teto diário)."""
    with _lock:
        d = _load()
        x = d["xp"]
        before = level_info(x["total"])["nivel"]
        x["total"] = int(x.get("total", 0)) + int(points)
        x["eventos"] = ([{"tipo": reason, "xp": int(points), "em": datetime.now().isoformat(timespec="seconds")}] + x.get("eventos", []))[:30]
        _save(d)
        info = level_info(x["total"])
        return {"ganhou": int(points), "subiu": info["nivel"] > before, **info}


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
    # cara de senha (curta, mista, SEM espaço). V9.0: o "sem espaço" agora vale de verdade; antes endereços e frases
    # ("Rua das Acácias, 123 - Maceió") eram tratados como senha e não entravam nos copiados.
    re.compile(r"^(?!.*\s)(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^\w\s]).{8,40}$"),
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


def clipboard_sequence() -> int | None:
    """V8.7.0: número que o Windows muda a cada cópia (barato; não abre a área de transferência).

    Antes o JARVIS ABRIA a área de transferência a cada 1,5 s, o que podia atrapalhar o copiar/colar dos outros
    programas. None fora do Windows (aí lê sempre)."""
    import sys

    if sys.platform != "win32":
        return None
    try:
        import ctypes

        return int(ctypes.windll.user32.GetClipboardSequenceNumber())
    except Exception:  # noqa: BLE001
        return None


async def clipboard_loop(interval: float = 1.5) -> None:
    """Vigia a área de transferência do PC (só Windows) e guarda o que for copiado."""
    import asyncio
    import logging
    import sys

    if sys.platform != "win32":
        return
    log = logging.getLogger("jarvis.desk")
    last = None
    seq = clipboard_sequence  # V8.7.0: só abre a área de transferência quando algo NOVO foi copiado
    last_seq = None
    while True:
        try:
            now_seq = seq()
            if now_seq is None or now_seq != last_seq:
                last_seq = now_seq
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
    try:
        from modules import desk_missions

        missoes = desk_missions.cloud_summary()
    except Exception:  # noqa: BLE001
        missoes = None
    return {"avatar": d["avatar"], "cor": d["cor"], "nivel": level_info(d["xp"]["total"]), "habitos": habits()["itens"],
            "tema": season_theme() if d["avatar"].get("temas", True) else None, "missoes": missoes}
