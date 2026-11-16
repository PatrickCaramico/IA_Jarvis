"""V8.1: MISSÕES e OFENSIVA do Modo Desk (ideia 7 do documento de atualização).

- Todo dia 3 missões novas (sem repetir as de ontem): 1 de usar o JARVIS, 1 pergunta sobre você e 1 de bem-estar.
  As de uso se completam sozinhas quando a ação acontece; as de bem-estar você marca; a pergunta você responde
  ali mesmo e a resposta vai para a memória.
- 1 desafio da semana (vale mais XP).
- Ofensiva: dias seguidos com pelo menos 1 missão feita. Ganha 1 protetor por semana (guarda até 2): se você
  perder um dia, o protetor segura a ofensiva.
- Itens do guarda-roupa liberam por nível e por ofensiva (recorde).
"""
from __future__ import annotations

import json
import random
import re
from datetime import date

from config import settings
from core.safe_io import replace_file
from modules import desk

_PATH = settings.DATA_DIR / "missoes.json"
_lock = desk._lock  # o mesmo lock do Modo Desk (as missões mexem no XP e o XP mexe nas missões)

XP_BY_TYPE = {"uso": 20, "sobre": 25, "bem": 15, "semana": 150}
MAX_SHIELDS = 2

# (id, texto, tipo de ação contada, quantas vezes)
USE = [
    ("uso_conversa", "Converse 3 vezes com o JARVIS", "conversa", 3),
    ("uso_tarefa", "Conclua 1 tarefa", "tarefa", 1),
    ("uso_lembrete", "Crie 1 lembrete", "lembrete", 1),
    ("uso_rotina", "Rode 1 rotina", "rotina", 1),
    ("uso_memoria", "Ensine 1 coisa nova ao JARVIS", "memoria", 1),
    ("uso_habito", "Marque 1 hábito do dia", "habito", 1),
    ("uso_holo", "Abra o Holograma", "holograma", 1),
    ("uso_olho", "Dê uma olhada no Olho de Deus", "olho", 1),
]
# (id, pergunta, como guardar na memória)
ABOUT = [
    ("sobre_comida", "Qual é a sua comida favorita?", "Comida favorita"),
    ("sobre_filme", "Qual filme você veria de novo hoje?", "Filme favorito"),
    ("sobre_musica", "Que música não sai da sua cabeça?", "Música do momento"),
    ("sobre_sonho", "Qual lugar você sonha em conhecer?", "Lugar dos sonhos"),
    ("sobre_hobby", "O que você gosta de fazer no tempo livre?", "Hobby"),
    ("sobre_meta", "Qual é a sua meta para este ano?", "Meta do ano"),
    ("sobre_bebida", "Café, chá ou suco pela manhã?", "Bebida da manhã"),
    ("sobre_serie", "Qual série você está assistindo?", "Série do momento"),
    ("sobre_jogador", "Quem é o seu jogador preferido?", "Jogador preferido"),
    ("sobre_livro", "Qual livro marcou você?", "Livro marcante"),
    ("sobre_animal", "Qual é o seu animal favorito?", "Animal favorito"),
    ("sobre_estacao", "Prefere frio ou calor?", "Clima preferido"),
]
FREE_ABOUT = ("sobre_livre", "Conte uma coisa nova sobre você", "Sobre mim")
WELL = [
    ("bem_agua", "Beba 2 copos de água"),
    ("bem_alongar", "Alongue-se por 5 minutos"),
    ("bem_caminhar", "Caminhe 10 minutos"),
    ("bem_tela", "Fique 15 minutos longe das telas"),
    ("bem_respirar", "Respire fundo por 1 minuto"),
    ("bem_fruta", "Coma uma fruta"),
    ("bem_dormir", "Durma antes da meia-noite"),
    ("bem_postura", "Arrume a postura e relaxe os ombros"),
]
WEEKLY = [
    ("sem_tarefas", "Conclua 10 tarefas nesta semana", "tarefa", 10),
    ("sem_conversa", "Converse 30 vezes com o JARVIS nesta semana", "conversa", 30),
    ("sem_missoes", "Complete 15 missões nesta semana", "missao", 15),
    ("sem_habitos", "Marque 12 hábitos nesta semana", "habito", 12),
]
ITEM_NAMES = {
    "gorro": "gorro", "bone": "boné", "fone": "fone", "cartola": "cartola", "gatinho": "tiara de gatinho",
    "bruxa": "chapéu de bruxa", "headset": "headset", "coroa": "coroa", "oculos": "óculos", "laco": "laço",
    "bigode": "bigode", "oculos_escuros": "óculos escuros", "cachecol": "cachecol", "gravata": "gravata-borboleta",
    "camisa": "camisa do time", "capa": "capa de herói", "armadura": "colete de armadura", "coracao": "olhos de coração",
    "estrela": "olhos de estrela", "aureola": "auréola", "chifrinhos": "chifrinhos", "festa": "chapéu de festa",
    "flor": "flor", "bone_time": "boné do time", "pixel": "olhos de pixel", "brilho": "brilho", "neve": "neve", "faiscas": "faíscas",
}


def _week_id(day: date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-W{w:02d}"


def _empty() -> dict:
    return {"dia": "", "itens": [], "semana": {}, "respondidas": [], "novos": [],
            "ofensiva": {"atual": 0, "recorde": 0, "ultimo_dia": "", "protetores": 0, "protetor_semana": ""}}


def _load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty()
    out = _empty()
    for k, v in data.items() if isinstance(data, dict) else ():
        if isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    replace_file(tmp, _PATH)  # V8.3.2: resiste ao OneDrive


def _pick(pool: list, rng: random.Random, avoid: set) -> tuple:
    options = [p for p in pool if p[0] not in avoid] or pool
    return rng.choice(options)


def _roll_day(st: dict, today: date) -> None:
    """Sorteia as 3 missões do dia (o sorteio é o mesmo para o mesmo dia; não repete as de ontem)."""
    rng = random.Random(f"jarvis-{today.isoformat()}")
    yesterday = {i["id"] for i in st.get("itens", [])}
    u = _pick(USE, rng, yesterday)
    answered = set(st.get("respondidas", []))
    open_q = [q for q in ABOUT if q[0] not in answered]
    a = _pick(open_q, rng, yesterday) if open_q else FREE_ABOUT
    w = _pick(WELL, rng, yesterday)
    st["dia"] = today.isoformat()
    st["itens"] = [
        {"id": u[0], "tipo": "uso", "texto": u[1], "acao": u[2], "meta": u[3], "progresso": 0, "feita": False, "xp": XP_BY_TYPE["uso"]},
        {"id": a[0], "tipo": "sobre", "texto": a[1], "rotulo": a[2], "meta": 1, "progresso": 0, "feita": False, "xp": XP_BY_TYPE["sobre"]},
        {"id": w[0], "tipo": "bem", "texto": w[1], "meta": 1, "progresso": 0, "feita": False, "xp": XP_BY_TYPE["bem"]},
    ]


def _roll_week(st: dict, today: date) -> None:
    wid = _week_id(today)
    if st.get("semana", {}).get("semana") != wid:
        rng = random.Random(f"jarvis-{wid}")
        c = _pick(WEEKLY, rng, {st.get("semana", {}).get("id", "")})
        st["semana"] = {"semana": wid, "id": c[0], "tipo": "semana", "texto": c[1], "acao": c[2], "meta": c[3],
                        "progresso": 0, "feita": False, "xp": XP_BY_TYPE["semana"]}
    of = st["ofensiva"]
    if of.get("protetor_semana") != wid:  # 1 protetor por semana, guarda até 2
        of["protetores"] = min(MAX_SHIELDS, int(of.get("protetores", 0)) + 1)
        of["protetor_semana"] = wid


def _ensure(st: dict, today: date) -> dict:
    if st.get("dia") != today.isoformat():
        _roll_day(st, today)
    _roll_week(st, today)
    return st


def _streak_hit(of: dict, today: date) -> bool:
    """Primeira missão do dia: soma 1 à ofensiva (usa protetor se pulou dia). Devolve True se usou protetor."""
    last = of.get("ultimo_dia") or ""
    if last == today.isoformat():
        return False
    used = False
    try:
        gap = (today - date.fromisoformat(last)).days
    except ValueError:
        gap = 0
    if gap == 1:
        of["atual"] = int(of.get("atual", 0)) + 1
    elif gap > 1 and int(of.get("protetores", 0)) >= gap - 1:
        of["protetores"] = int(of["protetores"]) - (gap - 1)
        of["atual"] = int(of.get("atual", 0)) + 1
        used = True
    else:
        of["atual"] = 1
    of["recorde"] = max(int(of.get("recorde", 0)), of["atual"])
    of["ultimo_dia"] = today.isoformat()
    return used


def _current_streak(of: dict, today: date) -> int:
    """A ofensiva que vale hoje (zera se já passou dia demais para os protetores segurarem)."""
    try:
        gap = (today - date.fromisoformat(of.get("ultimo_dia") or "")).days
    except ValueError:
        return 0
    return int(of.get("atual", 0)) if gap <= 1 + int(of.get("protetores", 0)) else 0


def _unlocked_now(record: int) -> set[str]:
    d = desk._load()
    return desk.unlocked_ids(desk.level_info(d["xp"]["total"])["nivel"], record)


def _complete(st: dict, item: dict, today: date) -> dict:
    """Marca a missão como feita: XP, ofensiva, desafio da semana e itens novos."""
    before = _unlocked_now(int(st["ofensiva"].get("recorde", 0)))
    item["feita"] = True
    item["progresso"] = item.get("meta", 1)
    xp = desk.add_xp_raw(int(item.get("xp", 0)), "missao")
    shield = False
    if item.get("tipo") != "semana":
        shield = _streak_hit(st["ofensiva"], today)
        wk = st.get("semana") or {}
        if wk.get("acao") == "missao" and not wk.get("feita"):
            wk["progresso"] = int(wk.get("progresso", 0)) + 1
            if wk["progresso"] >= wk["meta"]:
                _complete(st, wk, today)
    new = sorted(_unlocked_now(int(st["ofensiva"].get("recorde", 0))) - before)
    if new:
        st["novos"] = list(dict.fromkeys(st.get("novos", []) + new))
    return {"xp": xp, "protetor_usado": shield, "liberados": [_item_label(n) for n in new]}


def _item_label(ref: str) -> str:
    return ITEM_NAMES.get(ref.split(":", 1)[-1], ref.split(":", 1)[-1])


def view(today: date | None = None) -> dict:
    today = today or date.today()
    with _lock:
        st = _ensure(_load(), today)
        _save(st)
    of = st["ofensiva"]
    done = sum(1 for i in st["itens"] if i["feita"])
    return {
        "dia": st["dia"], "itens": st["itens"], "semana": st["semana"], "feitas": done, "total": len(st["itens"]),
        "ofensiva": {"atual": _current_streak(of, today), "recorde": int(of.get("recorde", 0)),
                     "protetores": int(of.get("protetores", 0)), "max_protetores": MAX_SHIELDS,
                     "feita_hoje": of.get("ultimo_dia") == today.isoformat()},
        "novos": [{"ref": n, "nome": _item_label(n)} for n in st.get("novos", [])],
    }


def streak_record() -> int:
    return int(_load()["ofensiva"].get("recorde", 0))


def track(kind: str, today: date | None = None) -> list[dict]:
    """Conta a ação nas missões de uso do dia e no desafio da semana; devolve as que completaram agora."""
    today = today or date.today()
    finished = []
    with _lock:
        st = _ensure(_load(), today)
        for item in [*st["itens"], st.get("semana") or {}]:
            if item.get("acao") == kind and not item.get("feita"):
                item["progresso"] = int(item.get("progresso", 0)) + 1
                if item["progresso"] >= item.get("meta", 1):
                    finished.append({"id": item["id"], "texto": item["texto"], **_complete(st, item, today)})
        _save(st)
    return finished


def mark_done(ref: str, today: date | None = None) -> dict:
    """Missão de bem-estar (você marca). As outras se completam sozinhas ou respondendo."""
    today = today or date.today()
    with _lock:
        st = _ensure(_load(), today)
        item = next((i for i in st["itens"] if i["id"] == ref), None)
        if not item:
            raise KeyError(ref)
        if item["tipo"] != "bem":
            raise ValueError("Essa missão se completa sozinha quando você faz a ação.")
        out = {} if item["feita"] else _complete(st, item, today)
        _save(st)
    return {**out, "missoes": view(today)}


def answer(ref: str, text: str, today: date | None = None) -> dict:
    """Pergunta sobre você: a resposta vai para a memória do JARVIS."""
    today = today or date.today()
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:300]
    if len(text) < 2:
        raise ValueError("Escreva a resposta.")
    with _lock:
        st = _ensure(_load(), today)
        item = next((i for i in st["itens"] if i["id"] == ref and i["tipo"] == "sobre"), None)
        if not item:
            raise KeyError(ref)
        if item["feita"]:
            return {"missoes": view(today)}
        out = _complete(st, item, today)
        if ref != FREE_ABOUT[0]:
            st["respondidas"] = list(dict.fromkeys(st.get("respondidas", []) + [ref]))
        _save(st)
    try:
        from modules import memory

        memory.remember(f"{item.get('rotulo', 'Sobre mim')}: {text}", source="missao")
    except Exception:  # noqa: BLE001
        pass
    return {**out, "missoes": view(today)}


def seen() -> None:
    """O app já mostrou o aviso de "item novo liberado"."""
    with _lock:
        st = _load()
        st["novos"] = []
        _save(st)


def handle_voice(norm: str) -> str | None:
    """"quais são minhas missões?" / "como está minha ofensiva?"."""
    if re.search(r"\b(minhas missoes|missoes de hoje|missoes do dia|quais (sao )?(as )?(minhas )?missoes)\b", norm):
        v = view()
        falta = [i["texto"] for i in v["itens"] if not i["feita"]]
        if not falta:
            return f"Missões de hoje todas feitas, senhor! Ofensiva de {v['ofensiva']['atual']} dias."
        return f"Hoje você fez {v['feitas']} de {v['total']} missões. Faltam: {'; '.join(falta)}."
    if re.search(r"\b(minha ofensiva|como (esta|anda|ta) (a |minha )?ofensiva|ofensiva de hoje)\b", norm):
        v = view()["ofensiva"]
        dias = f"{v['atual']} {'dia' if v['atual'] == 1 else 'dias'}"
        prot = f"{v['protetores']} {'protetor' if v['protetores'] == 1 else 'protetores'}"
        hoje = "" if v["feita_hoje"] else " Faça uma missão hoje para não perder."
        return f"Sua ofensiva está em {dias} (recorde {v['recorde']}), com {prot} guardados.{hoje}"
    return None


def cloud_summary() -> dict:
    v = view()
    v.pop("novos", None)
    return v

