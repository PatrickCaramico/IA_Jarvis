"""Skill Deep Brief (V8.11): pesquisa a fundo, resumo falado e um dossiê salvo, com as fontes.

Frases (caminho rápido, sem IA):
- "faz um dossiê sobre carros elétricos no Brasil", "monta um relatório sobre a reforma tributária",
  "prepara um resumo completo sobre o James Webb", "dossiê sobre energia solar"
- "quais são meus dossiês?"
- "lê o dossiê sobre carros elétricos" / "abre o dossiê da reforma tributária" (fala o resumo de novo e mostra o
  painel com tópicos e fontes)

Como funciona (20 a 60 s, o progresso aparece na tela como um agente):
  1. a IA divide o tema em até 4 ângulos (contexto, novidades, números, prós e contras);
  2. cada ângulo é pesquisado no Google ao mesmo tempo (Gemini com pesquisa), guardando as fontes de cada um;
  3. a IA junta tudo num dossiê: resumo para ouvir (3 a 5 frases), tópicos, seções e o que ainda está em aberto;
  4. o dossiê fica em data/dossies/<tema>-<data>.md e o cartão "DOSSIÊ" abre o painel completo com as fontes.
Usa 1 da cota diária da pesquisa profunda (a mesma de "pesquisa profunda sobre..."). Se a pesquisa profunda estiver
desligada nas configurações, pergunta se libera só desta vez. Sem chave do Gemini, avisa que ficou sem internet.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, skill

log = logging.getLogger("jarvis.skills.deep_brief")

_DIR = settings.DATA_DIR / "dossies"
_PATH = settings.DATA_DIR / "dossies.json"  # índice (título, resumo, tópicos e fontes de cada dossiê)
MAX_ANGLES = 4
MAX_SOURCES = 12
MAX_INDEX = 50
AGENT = {"agent": "deep_brief", "label": "Deep Brief", "icon": "🔎"}


# ------------------------------------------------------------------ partes puras
def slug(text: str) -> str:
    from skills.workspace.layouts import norm

    return re.sub(r"\s+", "-", norm(text))[:60].strip("-") or "dossie"


def original_text(message: str, norm_part: str) -> str:
    """O tema como foi dito (com acentos e maiúsculas), recortado da frase original; a regex casa sem acentos."""
    from modules.agents import _tail

    found = _tail(message, norm_part) if message else norm_part
    return re.sub(r"\s+", " ", found or norm_part).strip(" .,!?")


def parse_json(text: str) -> Any:
    """O primeiro objeto/lista JSON dentro da resposta da IA (ela às vezes põe ```json ... ``` em volta)."""
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text)
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except ValueError:
                continue
    return None


def default_angles(tema: str) -> list[str]:
    return [f"{tema}: o que é e contexto", f"{tema}: novidades e acontecimentos recentes",
            f"{tema}: números, dados e fatos principais", f"{tema}: prós, contras, riscos e opiniões divergentes"]


def clean_angles(raw: Any, tema: str) -> list[str]:
    items = raw.get("perguntas") if isinstance(raw, dict) else raw
    out = [str(q).strip()[:200] for q in (items or []) if isinstance(q, str) and len(q.strip()) > 5]
    return list(dict.fromkeys(out))[:MAX_ANGLES] or default_angles(tema)


def merge_sources(groups: list[list[dict]]) -> list[dict]:
    seen, out = set(), []
    for group in groups:
        for src in group or []:
            url = str(src.get("url") or "")
            if url and url not in seen:
                seen.add(url)
                out.append({"name": src.get("name") or "Fonte", "headline": src.get("headline") or src.get("name") or "",
                            "url": url})
    return out[:MAX_SOURCES]


def _sentences(text: str, n: int) -> str:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text or "") if len(p.strip()) > 12]
    return " ".join(parts[:n])


def build_dossier(raw: Any, tema: str, findings: list[tuple[str, str]]) -> dict:
    """Junta a resposta da IA (JSON) com o que foi pesquisado; se a IA não devolveu JSON, monta do material bruto."""
    data = raw if isinstance(raw, dict) else {}
    resumo = str(data.get("resumo_falado") or "").strip()
    if not resumo:
        resumo = _sentences(" ".join(t for _, t in findings), 4) or f"Não encontrei informações suficientes sobre {tema}."
    secoes = [s for s in data.get("secoes") or [] if isinstance(s, dict) and s.get("texto")]
    if not secoes:
        secoes = [{"titulo": q.split(":", 1)[-1].strip().capitalize() or q, "texto": t} for q, t in findings if t]
    pontos = [str(p).strip() for p in data.get("pontos") or [] if str(p).strip()][:8]
    if not pontos:
        pontos = [_sentences(t, 1) for _, t in findings if _sentences(t, 1)][:6]
    return {"titulo": str(data.get("titulo") or tema).strip()[:120], "resumo_falado": re.sub(r"[*#_`]", "", resumo),
            "pontos": pontos, "secoes": secoes[:8],
            "em_aberto": [str(p).strip() for p in data.get("em_aberto") or [] if str(p).strip()][:5]}


def render_markdown(dossier: dict, tema: str, sources: list[dict], when: datetime, web: bool) -> str:
    lines = [f"# {dossier['titulo']}", "",
             f"*Dossiê do JARVIS sobre “{tema}” · {when:%d/%m/%Y %H:%M}*"
             + ("" if web else " · *sem pesquisa na internet (Gemini não configurado)*"), "",
             "## Resumo", "", dossier["resumo_falado"], ""]
    if dossier["pontos"]:
        lines += ["## Principais pontos", ""] + [f"- {p}" for p in dossier["pontos"]] + [""]
    for sec in dossier["secoes"]:
        lines += [f"## {sec.get('titulo') or 'Detalhes'}", "", str(sec.get("texto") or "").strip(), ""]
    if dossier["em_aberto"]:
        lines += ["## Em aberto", ""] + [f"- {p}" for p in dossier["em_aberto"]] + [""]
    if sources:
        lines += ["## Fontes", ""] + [f"{i}. [{s['headline'] or s['name']}]({s['url']})" for i, s in enumerate(sources, 1)]
    return "\n".join(lines).rstrip() + "\n"


def card(entry: dict) -> dict:
    """Mesmo cartão da pesquisa profunda (o frontend abre o painel com tópicos e fontes)."""
    n = len(entry.get("fontes") or [])
    return {"type": "deep_search", "data": {
        "title": entry.get("titulo") or entry.get("tema"), "category": "DOSSIÊ · DEEP BRIEF",
        "reference": f"Salvo em data/dossies/{entry.get('arquivo', '')}", "badge": f"{n} FONTES" if n else "SEM FONTES",
        "metrics": [], "summary": entry.get("resumo", ""), "bullets": entry.get("pontos") or [],
        "sources": entry.get("fontes") or [], "time": entry.get("hora", "")}}


# ------------------------------------------------------------------ índice
def load_index() -> list[dict]:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else []
    except (OSError, ValueError):
        data = []
    return data if isinstance(data, list) else []


def find(tema: str, index: Optional[list[dict]] = None) -> Optional[dict]:
    """O dossiê mais recente cujo tema bate com o dito (igual, ou todas as palavras dele presentes)."""
    want = slug(tema)
    words = [w for w in want.split("-") if len(w) > 2]
    items = index if index is not None else load_index()
    for entry in items:  # o índice fica do mais novo para o mais velho
        if entry.get("slug") == want:
            return entry
    for entry in items:
        have = set(str(entry.get("slug", "")).split("-"))
        if words and all(w in have for w in words):
            return entry
    return None


def _save(entry: dict, markdown: str) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    safe_io.write_text(_DIR / entry["arquivo"], markdown)
    index = [e for e in load_index() if e.get("arquivo") != entry["arquivo"]]
    safe_io.write_json(_PATH, ([entry] + index)[:MAX_INDEX])


# ------------------------------------------------------------------ pesquisa
def _plan(tema: str) -> list[str]:
    from services import llm_orchestrator as llm

    prompt = (f'Vou pesquisar a fundo o tema "{tema}" no Google. Divida em {MAX_ANGLES} perguntas de pesquisa '
              "diferentes e objetivas (contexto, novidades recentes, números/dados, prós e contras ou opiniões "
              'divergentes), em português. Responda SÓ com JSON: {"perguntas": ["...", "..."]}')
    try:
        return clean_angles(parse_json(llm.ask_text(prompt, max_tokens=400)), tema)
    except Exception:  # noqa: BLE001 - sem plano da IA: usa os ângulos padrão
        log.warning("Deep Brief: plano da IA falhou; usando os ângulos padrão", exc_info=True)
        return default_angles(tema)


def _research(question: str) -> tuple[str, list[dict]]:
    from services import llm_orchestrator as llm

    prompt = (f"Pesquise na internet e responda em português, em até 8 frases objetivas e factuais, com datas, números "
              f"e nomes quando houver (sem markdown): {question}")
    return llm.ask_web(prompt, max_tokens=900)


def _synthesize(tema: str, findings: list[tuple[str, str]]) -> Any:
    from services import llm_orchestrator as llm

    material = "\n\n".join(f"### {q}\n{t}" for q, t in findings if t)[:12000]
    prompt = (f'Monte um dossiê em português sobre "{tema}" usando SÓ o material pesquisado abaixo (não invente; se '
              "houver divergência, diga). Responda SÓ com JSON no formato: "
              '{"titulo": "...", "resumo_falado": "3 a 5 frases curtas, para ler em voz alta, sem markdown", '
              '"pontos": ["até 8 tópicos curtos"], "secoes": [{"titulo": "...", "texto": "1 a 2 parágrafos"}], '
              '"em_aberto": ["o que ainda não está claro"]}\n\nMATERIAL:\n' + material)
    try:
        return parse_json(llm.ask_text(prompt, max_tokens=1800))
    except Exception:  # noqa: BLE001 - sem a síntese da IA: o dossiê sai do material bruto
        log.warning("Deep Brief: síntese da IA falhou; montando do material pesquisado", exc_info=True)
        return None


async def _progress(ctx: SkillContext, status: str, text: str) -> None:
    try:
        await ctx.broadcast({"type": "agent", **AGENT, "status": status, "text": text})
    except Exception:  # noqa: BLE001 - a tela fora do ar não para a pesquisa
        log.debug("Deep Brief: aviso de progresso não chegou", exc_info=True)


_ASK_RE = r"(?:faz|faca|fazer|monta|monte|montar|prepara|prepare|preparar|cria|crie|gera|gere|escreve|escreva)"
_TEMA = r"(?P<tema>[a-z0-9][a-z0-9 ,.'-]{2,120})$"


@skill(
    name="deep_brief",
    title="o dossiê",
    description="Pesquisa um tema a fundo na internet e monta um dossiê com resumo falado, tópicos e fontes.",
    permission=Permission.ACTION,
    llm=False,  # leva até 1 min: fica fora das funções da IA (que têm o prazo do turno)
    timeout=110,
    triggers=[rf"\b{_ASK_RE}\s+(?:um|uma)\s+(?:dossie|resumo completo|panorama completo|estudo completo)\s+"
              rf"(?:sobre|de|do|da|dos|das)\s+{_TEMA}",
              rf"\b{_ASK_RE}\s+(?:um|uma)\s+relatorio\s+(?:completo\s+)?sobre\s+{_TEMA}",
              rf"^(?:jarvis\s+)?dossie\s+(?:sobre|de|do|da)\s+{_TEMA}"],
    params={"type": "object", "required": ["tema"], "properties": {
        "tema": {"type": "string"}, "uma_vez": {"type": "boolean", "description": "Liberado só desta vez."}}},
    examples=["faz um dossiê sobre carros elétricos no Brasil"],
)
async def deep_brief(ctx: SkillContext, tema: str, uma_vez: bool = False) -> SkillResult:
    from core import confirm
    from modules import deep_search_quota, prefs

    tema = original_text(ctx.message, tema)
    if not tema:
        return SkillResult(ok=False, speech="Sobre qual tema monto o dossiê, senhor?")
    allowed = bool((await asyncio.to_thread(prefs.get_all)).get("deep_search_allowed", False))
    if not allowed and not uma_vez:
        confirm.offer("skill", {"name": "deep_brief", "args": {"tema": tema, "uma_vez": True}, "message": ctx.message,
                                "origin": "deep_brief", "remote": ctx.remote})
        return SkillResult(pending=True, speech=f"A pesquisa profunda está desligada, senhor. Libero só desta vez para o "
                                                f"dossiê sobre {tema}? Diga sim para pesquisar.")
    can, reason = await asyncio.to_thread(deep_search_quota.can_consume)
    if not can:
        return SkillResult(ok=False, speech=reason)
    await asyncio.to_thread(deep_search_quota.consume)

    started = time.monotonic()
    await _progress(ctx, "working", f"planejando a pesquisa sobre {tema}…")
    angles = await asyncio.to_thread(_plan, tema)
    await _progress(ctx, "working", f"pesquisando {len(angles)} ângulos ao mesmo tempo…")
    raw = await asyncio.gather(*(asyncio.to_thread(_research, q) for q in angles), return_exceptions=True)
    findings: list[tuple[str, str]] = []
    groups: list[list[dict]] = []
    for q, res in zip(angles, raw):
        if isinstance(res, BaseException):
            log.warning("Deep Brief: pesquisa '%s' falhou: %s", q, res)
            continue
        text, sources = res
        if text and text.strip():
            findings.append((q, text.strip()))
            groups.append(sources)
    if not findings:
        await asyncio.to_thread(deep_search_quota.refund)
        await _progress(ctx, "error", "a pesquisa não respondeu")
        return SkillResult(ok=False, speech="A pesquisa não respondeu agora, senhor. Não gastei a sua cota; tente de "
                                            "novo em instantes.")
    await _progress(ctx, "working", "montando o dossiê…")
    dossier = build_dossier(await asyncio.to_thread(_synthesize, tema, findings), tema, findings)
    sources = merge_sources(groups)
    now = datetime.now()
    entry = {"slug": slug(tema), "tema": tema, "titulo": dossier["titulo"], "resumo": dossier["resumo_falado"],
             "pontos": dossier["pontos"], "fontes": sources, "arquivo": f"{slug(tema)}-{now:%Y%m%d-%H%M}.md",
             "criado": now.isoformat(timespec="seconds"), "hora": f"{now:%H:%M}"}
    try:
        await asyncio.to_thread(_save, entry, render_markdown(dossier, tema, sources, now, web=bool(sources)))
        saved = True
    except OSError:
        log.exception("Deep Brief: não consegui salvar o dossiê")
        saved = False
    await _progress(ctx, "done", f"pronto em {time.monotonic() - started:.0f} s")
    tail = (f" O dossiê completo, com {len(sources)} {'fonte' if len(sources) == 1 else 'fontes'}, ficou salvo; "
            f"para ouvir de novo, diga: lê o dossiê sobre {tema}." if saved else
            " Não consegui salvar o arquivo do dossiê; o resumo ficou na tela.")
    if not sources:
        tail += " Aviso: desta vez a pesquisa ficou sem fontes da internet."
    return SkillResult(speech=dossier["resumo_falado"] + tail, cards=[card(entry)],
                       data={"titulo": entry["titulo"], "arquivo": entry["arquivo"]})


@skill(
    name="listar_dossies",
    title="listar os dossiês",
    description="Diz quais dossiês (pesquisas a fundo) estão salvos, do mais recente para o mais antigo.",
    permission=Permission.READ,
    timeout=5,
    triggers=[r"\b(?:quais|meus|lista|liste|mostra|mostre)\s+(?:sao\s+)?(?:os\s+)?(?:meus\s+)?dossies\b"],
    examples=["quais são meus dossiês?"],
)
def listar_dossies(ctx: SkillContext) -> SkillResult:
    from skills.workspace.layouts import spoken_list

    index = load_index()
    if not index:
        return SkillResult(speech="Ainda não há dossiês salvos, senhor. Diga, por exemplo: faz um dossiê sobre energia solar.")
    names = [e.get("tema", "") for e in index[:5]]
    rows = [{"label": str(e.get("criado", ""))[:10], "value": e.get("titulo") or e.get("tema")} for e in index[:15]]
    more = f" e mais {len(index) - 5}" if len(index) > 5 else ""
    return SkillResult(data={"dossies": [{"tema": e.get("tema"), "titulo": e.get("titulo"), "criado": e.get("criado"),
                                          "fontes": len(e.get("fontes") or [])} for e in index[:20]]},
                       speech=f"Dossiês salvos: {spoken_list(names)}{more}.",
                       cards=[{"type": "skill", "data": {"tag": "DOSSIÊS", "source": f"{len(index)} salvo(s)", "rows": rows}}])


@skill(
    name="ler_dossie",
    title="ler o dossiê",
    description="Lê de novo o resumo de um dossiê salvo e mostra o painel com tópicos e fontes.",
    permission=Permission.READ,
    timeout=5,
    triggers=[r"\b(?:le|leia|ler|abre|abra|abrir|mostra|mostre|repete|repita)\s+(?:o\s+|meu\s+)?dossie\s+"
              r"(?:sobre\s+|de\s+|do\s+|da\s+|dos\s+|das\s+)?(?P<tema>[a-z0-9][a-z0-9 ,.'-]{1,120})$"],
    params={"type": "object", "required": ["tema"], "properties": {"tema": {"type": "string"}}},
    examples=["lê o dossiê sobre carros elétricos"],
)
def ler_dossie(ctx: SkillContext, tema: str) -> SkillResult:
    tema = original_text(ctx.message, tema)
    entry = find(tema)
    if entry is None:
        return SkillResult(ok=False, speech=f"Não tenho um dossiê sobre {tema}, senhor. Quer que eu faça? Diga: faz um "
                                            f"dossiê sobre {tema}.")
    quando = str(entry.get("criado", ""))[:10].split("-")
    data_txt = f" (de {quando[2]}/{quando[1]})" if len(quando) == 3 else ""
    return SkillResult(speech=f"Dossiê sobre {entry.get('tema')}{data_txt}: {entry.get('resumo', '')}", cards=[card(entry)])
