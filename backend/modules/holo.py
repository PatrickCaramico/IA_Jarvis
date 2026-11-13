"""V7.1: HOLOGRAMA. Pesquisas viram uma tela viva em vez de só uma resposta falada.

- "Jarvis, me explica como funciona um buraco negro" -> APRESENTAÇÃO: 4 a 6 cenas animadas (ícone, título,
  pontos, um número em destaque) narradas pela voz do JARVIS, uma cena por fala, sozinha.
- "Jarvis, receita de bolo de cenoura" -> RECEITA VIVA: ingredientes para marcar (e mandar para a lista de
  compras), passos grandes e o MODO COZINHA ("próximo passo", "repete", timer do passo com um toque).

A tela é frontend/src/components/HoloStage.jsx; a nuvem tem a mesma montagem em netlify/nuvem/core.mjs.
A IA devolve um JSON; aqui ele é conferido e encurtado (nada de texto gigante quebrando a tela).
"""
from __future__ import annotations

import json
import re

KINDS = ("receita", "apresentacao")

_RECIPE = re.compile(r"\breceitas?\b", re.I)


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
        '"numero": {"valor": 0, "unidade": "ex.: anos-luz", "rotulo": "o que o número significa"}}]}\n'
        "De 4 a 6 cenas: começa com um gancho curioso, explica do simples ao surpreendente e fecha com uma "
        "curiosidade. Use \"numero\" só quando houver um dado real e marcante (senão, null). Seja correto: "
        "nada de dado inventado."
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
    scenes = []
    for scene in data.get("cenas") or []:
        if not isinstance(scene, dict) or not _short(scene.get("fala"), 400):
            continue
        num = scene.get("numero") if isinstance(scene.get("numero"), dict) else None
        value = _number(num.get("valor")) if num else None
        scenes.append({
            "icone": _short(scene.get("icone"), 8) or "✦",
            "titulo": _short(scene.get("titulo"), 70),
            "fala": _short(scene.get("fala"), 400),
            "pontos": [_short(p, 120) for p in scene.get("pontos") or [] if isinstance(p, str) and p.strip()][:3],
            "numero": {"valor": value, "unidade": _short(num.get("unidade"), 30), "rotulo": _short(num.get("rotulo"), 60)}
            if value is not None else None,
        })
    if len(scenes) < 2:
        raise ValueError("A apresentação veio vazia.")
    return {**base, "cenas": scenes[:7]}
