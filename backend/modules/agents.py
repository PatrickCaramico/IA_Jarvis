"""V6.8: sub-agentes do JARVIS.

O JARVIS recebe o pedido e, quando ele é de um especialista, entrega a tarefa a um agente. O agente
aparece na tela enquanto trabalha ("🧭 Agente de rotas: abrindo a rota para o trabalho...") e abre o
resultado no APARELHO DE ONDE VEIO O PEDIDO: pediu no celular, abre no celular (Google Maps, YouTube);
pediu no PC, abre no navegador do PC.

Agentes:
- Rotas (🧭): "meu trabalho fica na Av. Paulista, 1000" guarda o lugar; "quero ir para o trabalho",
  "me leva pra academia", "rota para o aeroporto de Guarulhos", "como chego no shopping Ibirapuera a pé"
  abre o Google Maps com a rota saindo de onde você está. Também: "quais são meus lugares?",
  "esquece o endereço da academia".
- Pesquisa (🔎): "abre o YouTube e pesquisa receita de bolo", "procura lofi no YouTube".

Para criar um agente novo: uma classe com `match(norm, original)` (devolve a tarefa ou None) e
`async run(task)` (devolve AgentResult), e uma linha em AGENTS.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, quote_plus

from config import settings
from modules.quick_replies import _norm

log = logging.getLogger("jarvis.agents")


@dataclass
class AgentResult:
    reply: str
    url: str = ""
    status: str = ""  # texto curto para o aviso da tela


# ------------------------------------------------------------------ lugares (agente de rotas)
_PATH = settings.DATA_DIR / "lugares.json"
_PLACE_WORDS = {"casa", "trabalho", "escritorio", "empresa", "faculdade", "escola", "academia", "igreja", "mae", "pai",
                "namorada", "namorado", "esposa", "marido", "clube", "consultorio", "dentista", "medico", "mercado"}
_NOT_PLACES = {"cama", "banheiro", "dormir", "cozinha", "sala", "quarto", "embora", "la", "ali", "aqui", "frente"}
_PLACEY = re.compile(r"\b(?:rua|r|av|avenida|alameda|travessa|rodovia|estrada|praca|shopping|aeroporto|estacao|parque|"
                     r"hospital|praia|restaurante|mercado|supermercado|farmacia|centro|bairro|condominio|terminal|"
                     r"rodoviaria|metro|posto|hotel|museu|estadio|arena|universidade|faculdade|escola|igreja)\b|\d")


def load_places() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else {}
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_place(key: str, address: str) -> None:
    data = load_places()
    data[key] = address
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def forget_place(key: str) -> bool:
    data = load_places()
    if key not in data:
        return False
    del data[key]
    _PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def _key(text: str) -> str:
    words = [w for w in _norm(text).split() if w not in {"o", "a", "os", "as", "meu", "minha", "do", "da", "de", "lugar", "endereco"}]
    return " ".join(words[:3])


def _tail(original: str, norm_part: str) -> str:
    """O trecho `norm_part` (sem acentos, como casou na regex) recortado do texto ORIGINAL, com acentos e
    pontuação ("av paulista 1000 sao paulo" -> "Av. Paulista, 1000 - São Paulo")."""
    want = norm_part.split()
    tokens = re.findall(r"\S+", original or "")
    norms = [_norm(t).split() for t in tokens]
    for i in range(len(tokens)):
        got, j = [], i
        while j < len(tokens) and len(got) < len(want):
            got += norms[j]
            j += 1
        if got == want and norms[i]:
            # tira pontuação solta do fim (".", "!", "?") e artigos do começo
            return re.sub(r"[.!?]+$", "", " ".join(tokens[i:j])).strip()
    return norm_part


def _label(text: str) -> str:
    return re.sub(r"^(?:o|a|os|as)\s+", "", text.strip(), flags=re.I)


_MODES = [
    (re.compile(r"\s*\b(?:a pe|andando|caminhando)\b"), "walking", " a pé"),
    (re.compile(r"\s*\b(?:de|por|com)\s+(?:onibus|metro|trem|transporte publico)\b"), "transit", " de transporte público"),
    (re.compile(r"\s*\b(?:de|com)\s+(?:bicicleta|bike|bici)\b"), "bicycling", " de bicicleta"),
    (re.compile(r"\s*\b(?:de|com)\s+(?:carro|moto|uber|taxi)\b"), "driving", " de carro"),
]


class RouteAgent:
    name, label, icon = "rotas", "Agente de rotas", "🧭"

    _SAVE = [
        re.compile(r"^(?:jarvis\s+)?(?:lembre que |lembra que |guarda que |anota que )?(?:o\s+)?(?:meu|minha)\s+((?:\w+\s?){1,3}?)\s+fica\s+(?:na|no|em|nas|nos)\s+(.{4,})$"),
        re.compile(r"^(?:jarvis\s+)?(?:o\s+)?endereco\s+d[oa]\s+(?:meu\s+|minha\s+)?((?:\w+\s?){1,3}?)\s+e\s+(?:na|no|em)?\s*(.{4,})$"),
        re.compile(r"^(?:jarvis\s+)?(?:salva|salve|guarda|guarde|grava|grave)\s+(?:o\s+)?endereco\s+d[oa]\s+(?:meu\s+|minha\s+)?((?:\w+\s?){1,3}?)\s*(?:como|:|,|e)?\s+(.{4,})$"),
    ]
    _GO = [
        (re.compile(r"\b(?:quero|preciso|vou|vamos|bora)\s+(?:ir|voltar)\s+(?:para|pra|pro|ao|a|no|na|ate|em)\s+(.+)$"), False),
        (re.compile(r"\b(?:me leva|me leve|leve me|me levar)\s+(?:para|pra|pro|ao|a|ate|no|na)\s+(.+)$"), True),
        (re.compile(r"\b(?:rota|caminho|trajeto|direcoes)\s+(?:para|pra|pro|ate|ao|a|do|da|no|na)\s+(.+)$"), True),
        (re.compile(r"\bcomo\s+(?:eu\s+)?(?:chego|faco para chegar|faco pra chegar|vou)\s+(?:no|na|ao|a|em|ate|pro|pra|para)\s+(.+)$"), True),
    ]
    _LIST = re.compile(r"\b(?:quais|mostra|mostre|lista)\b.*\b(?:meus lugares|meus enderecos|lugares salvos|enderecos salvos)\b")
    _FORGET = re.compile(r"\b(?:esquece|esqueca|apaga|apague|remove|remova)\s+(?:o\s+)?(?:endereco|lugar)\s+d[oa]\s+(?:meu\s+|minha\s+)?(.+)$")

    def match(self, norm: str, original: str) -> Optional[dict]:
        for rx in self._SAVE:
            m = rx.match(norm)
            if m:
                key = _key(m.group(1))
                if key and key not in _NOT_PLACES:
                    return {"kind": "save", "key": key, "address": _tail(original, m.group(2)).strip(" ,.")}
        if self._LIST.search(norm):
            return {"kind": "list"}
        m = self._FORGET.search(norm)
        if m:
            return {"kind": "forget", "key": _key(m.group(1))}
        for rx, explicit in self._GO:
            m = rx.search(norm)
            if not m:
                continue
            dest = m.group(1)
            mode, mode_txt = "driving", ""
            for mrx, value, txt in _MODES:
                if mrx.search(dest):
                    dest, mode, mode_txt = mrx.sub("", dest).strip(), value, txt
            key = _key(dest)
            places = load_places()
            if key in places:
                return {"kind": "go", "label": key, "address": places[key], "mode": mode, "mode_txt": mode_txt}
            first = key.split(" ")[0] if key else ""
            if not key or first in _NOT_PLACES:
                return None
            if first in _PLACE_WORDS and len(key.split()) <= 2:
                return {"kind": "ask", "key": key}
            # destino livre ("shopping Ibirapuera", "rua X 100"): só com pedido claro de rota ou cara de lugar
            if explicit or _PLACEY.search(dest) or len(key.split()) >= 3:
                text = _tail(original, dest)
                return {"kind": "go", "label": _label(text), "address": _label(text), "mode": mode, "mode_txt": mode_txt}
        return None

    async def run(self, task: dict) -> AgentResult:
        kind = task["kind"]
        if kind == "save":
            await asyncio.to_thread(save_place, task["key"], task["address"])
            return AgentResult(f"Guardado, senhor: {task['key']} fica em {task['address']}. "
                               f"Quando quiser, é só dizer: quero ir para {task['key']}.", status=f"{task['key']} salvo")
        if kind == "list":
            places = load_places()
            if not places:
                return AgentResult("Ainda não tenho lugares salvos, senhor. Diga, por exemplo: meu trabalho fica na Avenida Paulista, 1000.")
            return AgentResult("Seus lugares: " + "; ".join(f"{k}, {v}" for k, v in places.items()) + ".")
        if kind == "forget":
            ok = await asyncio.to_thread(forget_place, task["key"])
            return AgentResult(f"Pronto, esqueci o endereço de {task['key']}." if ok else "Não achei esse lugar salvo, senhor.")
        if kind == "ask":
            return AgentResult(f"Ainda não sei onde fica {task['key']}, senhor. Diga, por exemplo: "
                               f"meu {task['key']} fica na Rua tal, número tal. Aí é só pedir a rota.")
        url = ("https://www.google.com/maps/dir/?api=1&destination=" + quote(task["address"])
               + "&travelmode=" + task["mode"])
        dest = task["label"]
        return AgentResult(f"Abrindo a rota para {dest}{task['mode_txt']} no Google Maps, senhor.", url=url,
                           status=f"rota para {dest}{task['mode_txt']}")


class SearchAgent:
    name, label, icon = "pesquisa", "Agente de pesquisa", "🔎"

    _RX = [
        re.compile(r"\b(?:abre|abra|abrir|entra|entre|vai)\s+(?:no\s+|o\s+)?youtube\s+e\s+(?:pesquisa|pesquise|procura|procure|busca|busque|coloca|coloque|poe|ponha|toca|toque)\s+(?:por\s+|sobre\s+)?(.+)$"),
        re.compile(r"\b(?:pesquisa|pesquise|procura|procure|busca|busque)\s+(?:por\s+|sobre\s+)?(.+?)\s+no\s+youtube$"),
        re.compile(r"\b(?:toca|toque|coloca|coloque|poe|ponha)\s+(.+?)\s+no\s+youtube$"),
        re.compile(r"\byoutube\s*[,:]?\s*(?:pesquisa|pesquise|procura|procure|busca|busque)\s+(?:por\s+)?(.+)$"),
    ]

    def match(self, norm: str, original: str) -> Optional[dict]:
        for rx in self._RX:
            m = rx.search(norm)
            if m and m.group(1).strip():
                return {"query": _tail(original, m.group(1)).strip(" .,")}
        return None

    async def run(self, task: dict) -> AgentResult:
        q = task["query"]
        return AgentResult(f"Pesquisando {q} no YouTube, senhor.",
                           url="https://www.youtube.com/results?search_query=" + quote_plus(q),
                           status=f"buscando “{q}” no YouTube")


AGENTS = [RouteAgent(), SearchAgent()]


# ------------------------------------------------------------------ orquestração
async def _tell(agent, status: str, text: str) -> None:
    from core import runtime

    await runtime.manager.broadcast({"type": "agent", "agent": agent.name, "label": agent.label, "icon": agent.icon,
                                     "status": status, "text": text})


async def _open(url: str) -> str:
    """Abre no aparelho que pediu: celular (evento para a tela dele) ou navegador do PC. Devolve onde abriu."""
    from core import runtime, voice_route

    target = voice_route.current()
    if target:
        await runtime.manager.broadcast({"type": "open_url", "url": url, "client_id": target})
        return "phone"
    from modules import tools

    await asyncio.to_thread(tools._open_in_default_browser, url)  # noqa: SLF001
    return "pc"


async def handle(message: str) -> Optional[str]:
    """Entrega o pedido ao agente certo. None = nenhum agente cuida disso (segue o fluxo normal)."""
    norm = _norm(message or "")
    for agent in AGENTS:
        task = agent.match(norm, message)
        if task is None:
            continue
        log.info("Agente %s assumiu o pedido.", agent.name)
        await _tell(agent, "working", "trabalhando…")
        try:
            result = await agent.run(task)
            if result.url:
                await _open(result.url)
        except Exception as exc:  # noqa: BLE001
            log.exception("Agente %s falhou", agent.name)
            await _tell(agent, "error", "não consegui agora")
            return f"O {agent.label.lower()} não conseguiu agora, senhor: {exc}"
        await _tell(agent, "done", result.status or "pronto")
        return result.reply
    return None


def snapshot_places() -> dict:
    """Para a nuvem (o agente de rotas também funciona fora de casa)."""
    return load_places()
