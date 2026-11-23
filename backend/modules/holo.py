"""V7.1: HOLOGRAMA. Pesquisas viram uma tela viva em vez de só uma resposta falada.

- "Jarvis, me explica como funciona um buraco negro" -> APRESENTAÇÃO: 4 a 6 cenas animadas (ícone, título,
  pontos, um número em destaque) narradas pela voz do JARVIS, uma cena por fala, sozinha.
- "Jarvis, receita de bolo de cenoura" -> RECEITA VIVA: ingredientes para marcar (e mandar para a lista de
  compras), passos grandes e o MODO COZINHA ("próximo passo", "repete", timer do passo com um toque).

A tela é frontend/src/components/HoloStage.jsx; a nuvem tem a mesma montagem em netlify/nuvem/core.mjs.
A IA devolve um JSON; aqui ele é conferido e encurtado (nada de texto gigante quebrando a tela).

V8.14: a APRESENTAÇÃO pesquisa no Google antes (Gemini) e guarda as fontes (web_note + clean_sources), e as cenas
chegam aos poucos (partial_scenes lê as cenas já completas do JSON que a IA ainda está escrevendo).
"""
from __future__ import annotations

import json
import re

KINDS = ("receita", "apresentacao")
# V7.13: animação de cada cena (ideia 5): gráfico, linha do tempo, mapa ou diagrama de ciência
SCIENCE = ("sistema_solar", "atomo", "ciclo_agua", "coracao", "terra_camadas", "dna", "celula")
VISUAL_RULES = (
    "Em \"visual\", quando ajudar a entender, use UM destes (no máximo um por cena; varie entre as cenas; "
    "nas outras, null):\n"
    '- {"tipo": "grafico", "estilo": "barras|linha", "titulo": "curto", "unidade": "ex.: milhões", '
    '"dados": [{"rotulo": "2000", "valor": 6.1}]} com 2 a 8 pontos REAIS (anos, países, comparações);\n'
    '- {"tipo": "linha_do_tempo", "marcos": [{"data": "1969", "texto": "até 8 palavras"}]} com 2 a 6 marcos;\n'
    '- {"tipo": "mapa", "lugares": [{"nome": "Paris", "lat": 48.86, "lon": 2.35}], "rota": false} com 1 a 5 '
    "lugares (rota true liga os lugares na ordem, para viagens e rotas);\n"
    '- {"tipo": "ciencia", "modelo": "' + "|".join(SCIENCE) + '"} para espaço, átomo, água, corpo, Terra, genética.\n'
    "Nunca invente números ou datas: sem dado real, use null."
)

_RECIPE = re.compile(r"\breceitas?\b", re.I)


MAX_SOURCES = 6


def web_note() -> str:
    """V8.14: regra de veracidade da apresentação pesquisada (a mesma da conversa: services/grounding.WEB_NOTE)."""
    from services import grounding

    return ("\n" + grounding.WEB_NOTE + " Nas falas, não cite links nem números de referência; as fontes aparecem "
            "na tela no final.")


def clean_sources(items) -> list[dict]:
    """Fontes da pesquisa (do Gemini ou de uma apresentação salva): só https, sem repetir, no máximo 6."""
    out, seen = [], set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        url = _short(item.get("url"), 500)
        if not url.startswith("https://") or url in seen:
            continue
        seen.add(url)
        title = _short(item.get("titulo") or item.get("name") or item.get("headline"), 90) or "Fonte"
        out.append({"titulo": title, "url": url})
        if len(out) >= MAX_SOURCES:
            break
    return out


def guess_kind(query: str) -> str:
    return "receita" if _RECIPE.search(query or "") else "apresentacao"


def build_prompt(query: str, kind: str) -> str:
    q = re.sub(r"\s+", " ", query or "").strip()[:240]
    if kind == "receita":
        return (
            "Monte uma RECEITA para a tela do JARVIS (assistente em português do Brasil). Pedido do usuário: "
            f'"{q}".\nResponda SOMENTE com um JSON compacto, sem texto fora dele:\n'
            '{"tipo": "receita", "titulo": "nome da receita", "wiki": "nome do prato como título de artigo da Wikipédia", '
            '"fala": "1 frase curta apresentando a receita (vai ser falada)", "rende": "ex.: 8 fatias", '
            '"tempo": "ex.: 1h10", "dificuldade": "fácil|média|difícil", '
            '"ingredientes": ["quantidade + ingrediente, curto"], '
            '"passos": [{"texto": "passo curto e claro", "minutos": 0}], "dica": "1 dica de ouro"}\n'
            "Até 12 ingredientes e 8 passos. Em \"minutos\", ponha o tempo de espera do passo (forno, descanso, "
            "cozimento) ou 0. Receita real e testada; não invente ingrediente esquisito."
        )
    return (
        "Monte uma APRESENTAÇÃO curta e impressionante para a tela holográfica do JARVIS (assistente em português do "
        f'Brasil), explicando o assunto pedido: "{q}".\n'
        "Responda SOMENTE com um JSON compacto, sem texto fora dele:\n"
        '{"tipo": "apresentacao", "titulo": "título curto", "wiki": "assunto como título de artigo da Wikipédia", '
        '"cenas": [{"icone": "1 emoji", "titulo": "título da cena (até 6 palavras)", '
        '"fala": "1 ou 2 frases narradas pelo JARVIS, tom de documentário, tratando o usuário por senhor", '
        '"pontos": ["até 3 tópicos curtos"], '
        '"numero": {"valor": 0, "unidade": "ex.: anos-luz", "rotulo": "o que o número significa"}, '
        '"foto": "título de um artigo da Wikipédia com uma boa foto desta cena, ou null", '
        '"visual": null}]}\n'
        "De 4 a 6 cenas: começa com um gancho curioso, explica do simples ao surpreendente e fecha com uma "
        "curiosidade. Use \"numero\" só quando houver um dado real e marcante (senão, null). Seja correto: "
        "nada de dado inventado.\n" + VISUAL_RULES
    )


def _short(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _loads(raw: str):
    text = (raw or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("A IA não devolveu a tela.")
    try:
        return json.loads(match.group(0))
    except ValueError as exc:
        raise ValueError("A IA devolveu a tela incompleta.") from exc


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if "," in text or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):  # "4,6", "1.234,5", "384.400" (jeito brasileiro)
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text) if text else None
    except ValueError:
        return None


def clean_visual(v) -> dict | None:
    """Confere a animação da cena; qualquer coisa estranha vira None (a cena fica no modo de sempre)."""
    if not isinstance(v, dict):
        return None
    tipo = v.get("tipo")
    if tipo == "grafico":
        dados = []
        for d in v.get("dados") or []:
            if isinstance(d, dict):
                val = _number(d.get("valor"))
                if val is not None and _short(d.get("rotulo"), 20):
                    dados.append({"rotulo": _short(d.get("rotulo"), 20), "valor": val})
        if not 2 <= len(dados) <= 8:
            return None
        return {"tipo": "grafico", "estilo": "linha" if v.get("estilo") == "linha" else "barras",
                "titulo": _short(v.get("titulo"), 60), "unidade": _short(v.get("unidade"), 20), "dados": dados}
    if tipo == "linha_do_tempo":
        marcos = [{"data": _short(m.get("data"), 20), "texto": _short(m.get("texto"), 80)}
                  for m in v.get("marcos") or [] if isinstance(m, dict) and _short(m.get("data"), 20) and _short(m.get("texto"), 80)]
        return {"tipo": "linha_do_tempo", "marcos": marcos[:6]} if len(marcos) >= 2 else None
    if tipo == "mapa":
        lugares = []
        for lugar in v.get("lugares") or []:
            if not isinstance(lugar, dict):
                continue
            lat, lon = _number(lugar.get("lat")), _number(lugar.get("lon"))
            if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 and _short(lugar.get("nome"), 40):
                lugares.append({"nome": _short(lugar.get("nome"), 40), "lat": round(lat, 4), "lon": round(lon, 4)})
        return {"tipo": "mapa", "lugares": lugares[:5], "rota": bool(v.get("rota")) and len(lugares) > 1} if lugares else None
    if tipo == "ciencia" and v.get("modelo") in SCIENCE:
        return {"tipo": "ciencia", "modelo": v["modelo"]}
    return None


def parse(raw: str, kind: str) -> dict:
    """Confere o JSON da IA e devolve só o que a tela sabe mostrar. Lança ValueError se não der."""
    data = _loads(raw)
    if not isinstance(data, dict):
        raise ValueError("A IA não devolveu a tela.")
    tipo = data.get("tipo") if data.get("tipo") in KINDS else kind
    base = {"tipo": tipo, "titulo": _short(data.get("titulo"), 80), "wiki": _short(data.get("wiki"), 80)}
    if not base["titulo"]:
        raise ValueError("A IA não devolveu a tela.")
    if tipo == "receita":
        steps = []
        for step in data.get("passos") or []:
            if isinstance(step, str):
                step = {"texto": step}
            if isinstance(step, dict) and _short(step.get("texto"), 300):
                minutes = _number(step.get("minutos")) or 0
                steps.append({"texto": _short(step["texto"], 300), "minutos": int(max(0, min(minutes, 24 * 60)))})
        ingredients = [_short(i, 90) for i in data.get("ingredientes") or [] if isinstance(i, str) and i.strip()]
        if not steps or not ingredients:
            raise ValueError("A receita veio sem passos.")
        return {**base, "fala": _short(data.get("fala"), 300), "rende": _short(data.get("rende"), 30),
                "tempo": _short(data.get("tempo"), 30), "dificuldade": _short(data.get("dificuldade"), 15),
                "ingredientes": ingredients[:14], "passos": steps[:10], "dica": _short(data.get("dica"), 240)}
    scenes = [c for c in (clean_scene(scene) for scene in data.get("cenas") or []) if c]
    if len(scenes) < 2:
        raise ValueError("A apresentação veio vazia.")
    out = {**base, "cenas": scenes[:7]}
    sources = clean_sources(data.get("fontes"))
    if sources:
        out["fontes"] = sources  # V8.14 (apresentação salva guarda as fontes também)
    return out


def clean_scene(scene) -> dict | None:
    """Uma cena conferida e encurtada (ou None se não der para mostrar)."""
    if not isinstance(scene, dict) or not _short(scene.get("fala"), 400):
        return None
    num = scene.get("numero") if isinstance(scene.get("numero"), dict) else None
    value = _number(num.get("valor")) if num else None
    return {
        "icone": _short(scene.get("icone"), 8) or "✦",
        "titulo": _short(scene.get("titulo"), 70),
        "fala": _short(scene.get("fala"), 400),
        "pontos": [_short(p, 120) for p in scene.get("pontos") or [] if isinstance(p, str) and p.strip()][:3],
        "numero": {"valor": value, "unidade": _short(num.get("unidade"), 30), "rotulo": _short(num.get("rotulo"), 60)}
        if value is not None else None,
        "visual": clean_visual(scene.get("visual")),
        "foto": _short(scene.get("foto") if isinstance(scene.get("foto"), str) else "", 80),
    }


def _objects_in_array(text: str, start: int) -> list[str]:
    """Os objetos {...} JÁ FECHADOS dentro do array que começa em text[start] == "[" (respeita textos entre aspas)."""
    out, depth, in_str, esc, obj_start = [], 0, False, False, -1
    for i in range(start + 1, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start >= 0:
                out.append(text[obj_start:i + 1])
                obj_start = -1
        elif ch == "]" and depth == 0:
            break
    return out


def partial_scenes(raw: str) -> list[dict]:
    """V8.14: cenas completas do JSON que a IA ainda está escrevendo (a tela começa sem esperar o resto)."""
    m = re.search(r'"cenas"\s*:\s*\[', raw or "")
    if not m:
        return []
    scenes = []
    for chunk in _objects_in_array(raw, m.end() - 1):
        try:
            scene = clean_scene(json.loads(chunk))
        except ValueError:
            continue
        if scene:
            scenes.append(scene)
    return scenes[:7]


def partial_title(raw: str) -> str:
    m = re.search(r'"titulo"\s*:\s*"((?:[^"\\]|\\.)*)"', raw or "")
    if not m:
        return ""
    try:
        return _short(json.loads(f'"{m.group(1)}"'), 80)
    except ValueError:
        return _short(m.group(1), 80)
