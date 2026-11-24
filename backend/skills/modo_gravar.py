"""Modo gravar (V9.4): o senhor ensina o JARVIS a fazer uma sequência de coisas e depois pede tudo de uma vez.

Antes: para juntar várias ações num comando só, era preciso montar um protocolo em Configurações > Protocolos, com
uma lista fixa de ações (abrir, volume, foco...). Agora é por demonstração:
  1. "modo gravar" (ou "vou te ensinar uma rotina chamada estudo"): o JARVIS começa a gravar e mostra ⏺ GRAVANDO;
  2. o senhor pede as coisas normalmente ("abre o Spotify", "organiza as janelas lado a lado", "volume 30"...).
     Cada pedido que deu certo vira um passo: as Skills com os parâmetros exatos e as funções locais pela frase;
  3. "para de gravar" (ou "salva como estudo") guarda a rotina;
  4. depois, "estudo" (o nome sozinho) ou "executa a rotina estudo" refaz tudo, na ordem.

Segurança: o que a IA só respondeu (conversa, pesquisa) não vira passo, e cada passo roda pelas mesmas regras de
sempre (permissões, prazo, central liberada). Uma ação crítica gravada pergunta o "sim" de novo ao refazer.
Os dados ficam em data/gravacoes.json. Máximo de 20 rotinas e 15 passos em cada.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, skill
from core.skills import executor as _executor

log = logging.getLogger("jarvis.skills.modo_gravar")

_PATH = settings.DATA_DIR / "gravacoes.json"
MAX_ITEMS = 20
MAX_STEPS = 15
STEP_PAUSE_S = 1.0
# As skills do próprio modo gravar não viram passo (nem as de só consultar a lista)
OWN = {"gravar_inicio", "gravar_fim", "gravar_cancelar", "listar_gravacoes", "apagar_gravacao"}

_state: Optional[dict] = None  # cópia em memória do arquivo (o observador roda a cada pedido)


# ------------------------------------------------------------------ dados
def _slug(text: str) -> str:
    from modules.quick_replies import _norm

    return _norm(text)[:60]


def _load() -> dict:
    global _state
    if _state is None:
        try:
            data = safe_io.read_json(_PATH) if _PATH.exists() else {}
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("items", {})
        data.setdefault("recording", None)
        _state = data
    return _state


def _save() -> None:
    safe_io.write_json(_PATH, _load())


def _save_later() -> None:
    """Grava o arquivo fora do laço principal (o observador é chamado no meio do pedido)."""
    from core import runtime

    try:
        asyncio.get_running_loop()
    except RuntimeError:  # sem laço rodando (testes síncronos)
        _save()
        return
    runtime.track(asyncio.to_thread(_save))


def reset_for_tests() -> None:
    global _state
    _state = None


def recording() -> Optional[dict]:
    return _load().get("recording")


def items() -> dict:
    return _load()["items"]


def find(name: str) -> Optional[tuple[str, dict]]:
    slug = _slug(name)
    if not slug:
        return None
    for prefix in ("", "rotina ", "a rotina ", "gravacao ", "a gravacao ", "o atalho "):
        if slug.startswith(prefix) and slug[len(prefix):] in items():
            key = slug[len(prefix):]
            return key, items()[key]
    return None


def describe_step(step: dict) -> str:
    if step.get("kind") == "skill":
        return step.get("message") or step["name"].replace("_", " ")
    return step.get("message", "")


# ------------------------------------------------------------------ o observador (grava cada pedido que deu certo)
def on_event(event: dict) -> None:
    rec = recording()
    if not rec or len(rec["steps"]) >= MAX_STEPS:
        return
    if event.get("kind") == "skill":
        if event.get("name") in OWN:
            return
        step = {"kind": "skill", "name": event["name"], "args": dict(event.get("args") or {}),
                "message": (event.get("message") or "")[:200]}
    elif event.get("kind") == "phrase" and event.get("message"):
        step = {"kind": "phrase", "message": event["message"][:200]}
    else:
        return
    rec["steps"].append(step)
    rec["last"] = time.time()
    _save_later()
    _announce()


_executor.observe(on_event)


def _event() -> dict:
    rec = recording()
    return {"type": "recording", "active": bool(rec), "label": (rec or {}).get("label", ""),
            "steps": len((rec or {}).get("steps") or []), "max": MAX_STEPS}


def _announce() -> None:
    """Do observador (dentro do laço principal): a central atualiza o ⏺ GRAVANDO com o número de passos."""
    from core import runtime

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    runtime.track(runtime.manager.broadcast(_event()))


async def _finish(ctx: SkillContext) -> None:
    await asyncio.to_thread(_save)
    await ctx.broadcast(_event())


# ------------------------------------------------------------------ gatilhos
_NAME = r"(?:\s+(?:chamad[oa]|com o nome(?: de)?|de nome|que se chama)\s+(?P<nome>[a-z0-9 ]{2,40}))?"
_START = [
    re.compile(r"^(?:jarvis\s+)?(?:entra(?:r)? no |ativa(?:r)? o |liga(?:r)? o )?modo (?:gravar|aprendizado|ensinar|aprender)$"),
    re.compile(r"\b(?:comeca|comece|inicia|inicie|pode comecar)\s+(?:a\s+)?gravar\b(?!.*\b(?:tela|video|audio|reuniao|voz)\b)"
               + _NAME),
    re.compile(r"\bvou te ensinar\b(?:\s+a fazer)?(?:\s+(?:uma?|a|o)\s+(?:rotina|atalho|sequencia|coisa))?" + _NAME),
    re.compile(r"\b(?:grava|grave|aprende|aprenda)\s+(?:uma?|a|o)\s+(?:rotina|atalho|sequencia|macro)" + _NAME),
]
_STOP = [
    re.compile(r"\b(?:para|pare|parar|pode parar|termina|termine|terminar|encerra|encerre|finaliza|finalize)\s+"
               r"(?:de\s+gravar|a\s+gravacao)\b(?:\s+(?:e\s+)?(?:salva|chama|grava)\s+(?:como|de)\s+(?P<nome>[a-z0-9 ]{2,40}))?"),
    re.compile(r"\b(?:fim da gravacao|terminei de (?:te )?ensinar)\b"),
    re.compile(r"\bsalva(?:r)?\s+(?:a\s+)?(?:gravacao|rotina)(?:\s+(?:como|com o nome(?: de)?)\s+(?P<nome>[a-z0-9 ]{2,40}))?$"),
    re.compile(r"^(?:pronto\s+)?(?:salva|chama|grava)\s+(?:isso\s+)?(?:como|de)\s+(?P<nome>[a-z0-9 ]{2,40})$"),
]
_CANCEL = re.compile(r"\b(?:cancela|cancele|cancelar|descarta|descarte|esquece|esqueca)\s+(?:a\s+)?gravacao\b")
_LIST = re.compile(r"\b(?:quais (?:sao )?(?:as )?(?:minhas )?(?:gravacoes|rotinas gravadas)|lista(?:r)? (?:as )?(?:minhas )?"
                   r"(?:gravacoes|rotinas gravadas)|o que (?:voce )?(?:ja )?aprendeu (?:comigo|a fazer))\b")
_RUN = re.compile(r"\b(?:faz|faca|fazer|executa|execute|executar|roda|rode|rodar|inicia|inicie|ativa|ative|reproduz|"
                  r"reproduza|repete|repita)\s+(?:a\s+|o\s+)?(?:rotina|gravacao|atalho)\s+(?P<nome>[a-z0-9 ]{2,40})$")
_DELETE = re.compile(r"\b(?:apaga|apague|exclui|exclua|deleta|delete|remove|remova)\s+(?:a\s+|o\s+)?(?:rotina|gravacao|atalho)"
                     r"(?:\s+gravad[oa])?\s+(?P<nome>[a-z0-9 ]{2,40})$")


def _clean_name(raw: Optional[str]) -> str:
    name = re.sub(r"\s+", " ", (raw or "")).strip()
    name = re.sub(r"^(?:a|o|de|do|da)\s+", "", name)
    return name


def _parse_start(norm: str, _original: str) -> Optional[dict]:
    if recording():
        return None
    for rx in _START:
        m = rx.search(norm)
        if m:
            nome = _clean_name(m.groupdict().get("nome"))
            return {"nome": nome} if nome else {}
    return None


def _parse_stop(norm: str, _original: str) -> Optional[dict]:
    if not recording():
        return None
    for rx in _STOP:
        m = rx.search(norm)
        if m:
            nome = _clean_name(m.groupdict().get("nome"))
            return {"nome": nome} if nome else {}
    return None


def _parse_cancel(norm: str, _original: str) -> Optional[dict]:
    return {} if recording() and _CANCEL.search(norm) else None


def _parse_run(norm: str, _original: str) -> Optional[dict]:
    if not items():
        return None
    m = _RUN.search(norm)
    if m and find(m.group("nome")):
        return {"nome": find(m.group("nome"))[0]}
    # o nome sozinho ("estudo", "modo estudo", "jarvis estudo") também vale, quando não está gravando
    if not recording():
        bare = re.sub(r"^(?:jarvis\s+)?", "", norm)
        if bare in items():
            return {"nome": bare}
    return None


def _parse_delete(norm: str, _original: str) -> Optional[dict]:
    m = _DELETE.search(norm)
    if m and items() and find(m.group("nome")):
        return {"nome": find(m.group("nome"))[0]}
    return None


# ------------------------------------------------------------------ skills
@skill(
    name="gravar_inicio",
    title="começar a gravar uma rotina",
    description=("Modo gravar: começa a gravar os próximos pedidos do usuário para formar uma rotina que ele chama "
                 "depois pelo nome. Use quando ele disser que vai ensinar algo ao JARVIS."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=5,
    parse=_parse_start,
    params={"type": "object", "properties": {"nome": {"type": "string", "description": "nome da rotina (opcional)"}}},
    examples=["modo gravar", "vou te ensinar uma rotina chamada estudo"],
)
async def gravar_inicio(ctx: SkillContext, nome: str = "") -> SkillResult:
    if recording():
        return SkillResult(speech="Já estou gravando, senhor. Quando terminar, diga: para de gravar.")
    if len(items()) >= MAX_ITEMS:
        return SkillResult(ok=False, speech=f"Já tenho {MAX_ITEMS} rotinas gravadas, senhor. Apague uma antes: "
                                            "diga apaga a rotina e o nome.")
    _load()["recording"] = {"label": _clean_name(nome), "steps": [], "started": time.time(), "last": time.time()}
    await _finish(ctx)
    called = f" a rotina {_clean_name(nome)}" if nome else ""
    return SkillResult(speech=f"Gravando{called}, senhor. Faça os pedidos normalmente; quando terminar, diga: para de gravar.")


@skill(
    name="gravar_fim",
    title="salvar a rotina gravada",
    description="Termina o modo gravar e salva a rotina com o nome dado (ou o nome dito no começo).",
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=5,
    parse=_parse_stop,
    params={"type": "object", "properties": {"nome": {"type": "string"}}},
    examples=["para de gravar", "salva como estudo"],
)
async def gravar_fim(ctx: SkillContext, nome: str = "") -> SkillResult:
    rec = recording()
    if not rec:
        return SkillResult(speech="Não estou gravando nada agora, senhor. Para começar, diga: modo gravar.")
    data = _load()
    if not rec["steps"]:
        data["recording"] = None
        await _finish(ctx)
        return SkillResult(speech="Parei a gravação, senhor, mas nenhum pedido deu certo nesse meio tempo; não salvei nada.")
    label = _clean_name(nome) or rec.get("label") or f"rotina {len(items()) + 1}"
    key = _slug(label)
    replaced = key in items()
    items()[key] = {"label": label, "steps": rec["steps"], "created": datetime.now().isoformat(timespec="seconds"), "runs": 0}
    data["recording"] = None
    await _finish(ctx)
    n = len(rec["steps"])
    again = " Substituí a anterior com esse nome." if replaced else ""
    return SkillResult(
        speech=f"Rotina {label} salva com {n} {'passo' if n == 1 else 'passos'}, senhor.{again} Para refazer, é só dizer: {label}.",
        cards=[_card(label, rec["steps"])],
    )


@skill(
    name="gravar_cancelar",
    title="cancelar a gravação",
    description="Cancela o modo gravar sem salvar nada.",
    permission=Permission.ACTION,
    timeout=5,
    parse=_parse_cancel,
    params={"type": "object", "properties": {}},
    examples=["cancela a gravação"],
)
async def gravar_cancelar(ctx: SkillContext) -> SkillResult:
    if not recording():
        return SkillResult(speech="Não estou gravando nada, senhor.")
    _load()["recording"] = None
    await _finish(ctx)
    return SkillResult(speech="Gravação cancelada, senhor. Nada foi salvo.")


def _card(label: str, steps: list[dict]) -> dict:
    rows = [{"label": f"Passo {i}", "value": describe_step(s)} for i, s in enumerate(steps, 1)]
    return {"type": "skill", "data": {"tag": "ROTINA GRAVADA", "source": label, "rows": rows}}


@skill(
    name="listar_gravacoes",
    title="ver as rotinas gravadas",
    description="Lista as rotinas que o usuário ensinou no modo gravar.",
    permission=Permission.READ,
    timeout=5,
    triggers=[_LIST.pattern],
    params={"type": "object", "properties": {}},
    examples=["quais são as minhas gravações?"],
)
def listar_gravacoes(ctx: SkillContext) -> SkillResult:
    from skills.workspace.layouts import spoken_list

    all_items = items()
    if not all_items:
        return SkillResult(speech="Ainda não aprendi nenhuma rotina, senhor. Para me ensinar, diga: modo gravar.")
    names = [v["label"] for v in all_items.values()]
    rows = [{"label": v["label"], "value": f"{len(v['steps'])} passos: " + "; ".join(describe_step(s) for s in v["steps"][:5])}
            for v in all_items.values()]
    return SkillResult(speech=f"Sei fazer {len(names)} {'rotina' if len(names) == 1 else 'rotinas'}, senhor: {spoken_list(names)}.",
                       cards=[{"type": "skill", "data": {"tag": "ROTINAS GRAVADAS", "source": f"{len(names)} no total", "rows": rows}}],
                       data={"rotinas": names})


@skill(
    name="executar_gravacao",
    title="fazer a rotina gravada",
    description="Refaz, na ordem, os passos de uma rotina ensinada no modo gravar.",
    permission=Permission.ACTION,
    timeout=120,
    llm=False,  # pode passar do prazo de um turno da IA (cada passo é um pedido inteiro)
    parse=_parse_run,
    params={"type": "object", "required": ["nome"], "properties": {"nome": {"type": "string"}}},
    examples=["estudo", "executa a rotina estudo"],
)
async def executar_gravacao(ctx: SkillContext, nome: str) -> SkillResult:
    from core.skills import registry
    from modules import tools

    hit = find(nome)
    if not hit:
        return SkillResult(ok=False, speech=f"Não conheço a rotina {nome}, senhor. Diga quais são as minhas gravações para ver a lista.")
    key, item = hit
    label, steps = item["label"], list(item["steps"])
    agent = {"type": "agent", "agent": "gravacao", "label": f"Rotina {label}", "icon": "⏺"}
    said, failed = [], []
    for i, step in enumerate(steps, 1):
        await ctx.broadcast({**agent, "status": "working", "text": f"Passo {i} de {len(steps)}: {describe_step(step)}"})
        try:
            if step["kind"] == "skill":
                result = await ctx.call(step["name"], **(step.get("args") or {}))
                if result.pending:  # ação crítica: pergunta o "sim" e para aqui
                    await ctx.broadcast({**agent, "status": "done", "text": f"Parei no passo {i}: falta o seu sim."})
                    return SkillResult(speech=f"Fiz {i - 1} de {len(steps)} passos da rotina {label}. {result.speech}")
                sk = registry.get(step["name"])
                if not result.ok:
                    failed.append(describe_step(step))
                elif sk is not None and sk.permission is Permission.READ and result.speech:
                    said.append(result.speech)
            else:
                reply = await tools.run(step["message"], ctx.user_name)
                if not reply:
                    failed.append(describe_step(step))
        except Exception:  # noqa: BLE001 - um passo com defeito não derruba os outros
            log.exception("Rotina %s: o passo %d falhou", label, i)
            failed.append(describe_step(step))
        if i < len(steps):
            await asyncio.sleep(STEP_PAUSE_S)
    item["runs"] = int(item.get("runs") or 0) + 1
    await asyncio.to_thread(_save)
    status = "error" if failed and len(failed) == len(steps) else "done"
    await ctx.broadcast({**agent, "status": status, "text": "Pronto." if not failed else f"{len(failed)} passo(s) falharam."})
    speech = f"Pronto, senhor: rotina {label} feita." if not failed else (
        f"Rotina {label} feita, senhor, mas não consegui: {failed[0]}." if len(failed) == 1
        else f"Rotina {label} feita em parte, senhor: {len(failed)} passos não deram certo. O detalhe ficou no log.")
    if said:
        speech += " " + " ".join(said[:2])
    return SkillResult(speech=speech, cards=[_card(label, steps)])


@skill(
    name="apagar_gravacao",
    title="apagar a rotina gravada",
    description="Apaga uma rotina ensinada no modo gravar.",
    permission=Permission.CRITICAL,
    allow_remote=False,
    timeout=5,
    parse=_parse_delete,
    params={"type": "object", "required": ["nome"], "properties": {"nome": {"type": "string"}}},
    confirm_text=lambda a: f"Apagar a rotina {a.get('nome', '')}, senhor? Diga sim para confirmar.",
    examples=["apaga a rotina estudo"],
)
def apagar_gravacao(ctx: SkillContext, nome: str) -> SkillResult:
    hit = find(nome)
    if not hit:
        return SkillResult(ok=False, speech=f"Não encontrei a rotina {nome}, senhor.")
    key, item = hit
    del items()[key]
    _save()
    return SkillResult(speech=f"Rotina {item['label']} apagada, senhor.")
