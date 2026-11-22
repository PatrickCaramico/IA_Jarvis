"""Orquestrador: junta visão + notícias + histórico + mensagem do usuário e consulta o LLM."""
import asyncio
import base64
import logging
import threading
import time
from datetime import datetime
from contextvars import ContextVar
from typing import Awaitable, Callable, Optional

from config import settings
from modules.about import get_about
from modules.face import get_name
from modules.news import fetch_top_news
from modules import prefs
from modules import memory
from modules.vision import capture_webcam_frame

log = logging.getLogger("jarvis.llm")

# Controle de cooldown de cota de API (429 / ResourceExhausted)
_quota_cooldown_until: float = 0.0
_quota_cooldown_reason: str = ""


def _is_timeout(exc: BaseException) -> bool:
    """V8.11: a IA não respondeu a tempo (cada biblioteca tem a sua exceção; o nome e o texto bastam)."""
    if isinstance(exc, TimeoutError):
        return True
    text = f"{type(exc).__name__} {exc}".lower()
    return "timeout" in text or "timed out" in text or "deadline" in text


def set_quota_cooldown(seconds: int = 60, reason: str = "Cota de requisições excedida") -> None:
    """Ativa período de espera para evitar chamadas contínuas após receber erro 429."""
    global _quota_cooldown_until, _quota_cooldown_reason
    _quota_cooldown_until = time.time() + max(1, seconds)
    _quota_cooldown_reason = reason


def get_quota_cooldown() -> tuple[bool, int]:
    """Retorna (está_em_cooldown, segundos_restantes)."""
    now = time.time()
    if now < _quota_cooldown_until:
        return True, max(1, int(_quota_cooldown_until - now))
    return False, 0


def is_quota_error(exc: Exception) -> bool:
    """Verifica se a exceção recebida é de cota esgotada ou limite de taxa (429/ResourceExhausted)."""
    msg = str(exc).lower()
    return any(k in msg for k in (
        "429", "resource_exhausted", "quota", "rate limit", "too many requests", "rate_limit_exceeded"
    ))

class _ToolSession:
    """V8.11: Skills oferecidas à IA neste turno (function calling). Vive numa ContextVar: o asyncio.to_thread
    copia o contexto, então a thread da IA enxerga a sessão e devolve aqui os cartões das skills."""

    def __init__(self, loop, skills, message: str, user_name: str, device, remote: bool) -> None:
        self.loop, self.skills = loop, skills
        self.message, self.user_name, self.device, self.remote = message, user_name, device, remote
        self.cards: list[dict] = []
        self.called: list[str] = []

    def run(self, name: str, args: dict):
        from core.skills import executor
        from core.skills.base import SkillContext

        ctx = SkillContext(message=self.message, origin="llm", user_name=self.user_name, device=self.device,
                           remote=self.remote)
        self.called.append(name)
        result = executor.run_from_thread(self.loop, name, args or {}, ctx)
        self.cards.extend(result.cards or [])
        return result


_tools_var: ContextVar[Optional[_ToolSession]] = ContextVar("jarvis_llm_tools", default=None)
_skill_cards_var: ContextVar[list] = ContextVar("jarvis_skill_cards", default=[])
MAX_TOOL_CALLS = 3


def take_skill_cards() -> list[dict]:
    """Cartões das Skills que a IA chamou no último turno (core/turns.py junta com os outros)."""
    cards = list(_skill_cards_var.get())
    _skill_cards_var.set([])
    return cards


def _system_text(ts: Optional[_ToolSession]) -> str:
    if ts is None:
        return SYSTEM_PROMPT
    from core.skills.llm_adapters import TOOL_GUIDE

    return f"{SYSTEM_PROMPT} {TOOL_GUIDE}"


def _tool_payload(result) -> dict:
    """O que volta para a IA depois de uma skill (para ela montar a frase final)."""
    return {"ok": result.ok, "fala": result.speech, "dados": result.data or {}, "aguardando_confirmacao": result.pending}


def _after_skills(results: list) -> str:
    """Frase de reserva quando a IA não conseguiu explicar o resultado das Skills."""
    said = " ".join(r.speech.strip() for r in results if r.speech)
    if said:
        return said
    return "Pronto, senhor." if all(r.ok for r in results) else "Não consegui concluir essa ação, senhor."


def _spoken(results: list) -> Optional[str]:
    """Todas as skills já trouxeram a frase pronta? Então nem precisa voltar à IA (economiza uma ida)."""
    if results and all(r.speech for r in results):
        return " ".join(r.speech.strip() for r in results)
    return None


class LLMTimeout(RuntimeError):
    """V8.11: o turno passou do LLM_TURN_BUDGET_S sem resposta da IA."""


# on_step("camera", "active" | "done" | "error")
StepCallback = Callable[[str, str], Awaitable[None]]

SYSTEM_PROMPT = (
    # Tom de voz do Branding Book 4.2: mordomo digital competente, discreto e leal (Sábio + Cuidador).
    "Você é J.A.R.V.I.S., o assistente pessoal do usuário: um mordomo digital competente, discreto e leal. "
    "Fale sempre em português do Brasil, com tom formal e cordial. Trate o usuário por 'senhor', sem "
    "repetir o tratamento em todas as frases. "
    "Suas respostas são LIDAS EM VOZ ALTA, como um assistente de voz: a resposta primeiro, em 1 a 3 frases "
    "curtas (só se alongue se o usuário pedir detalhes), sem listas, sem markdown, sem emojis e sem "
    "excesso de exclamações. Seja educado e caloroso: comece com uma confirmação breve e natural quando "
    "fizer sentido ('Claro, senhor.', 'Certo.', 'Com prazer.') e agradeça quando o usuário agradecer. "
    "Quando a resposta vier de uma pesquisa na internet, diga a fonte em poucas palavras ('segundo o ge', "
    "'de acordo com a CNN Brasil') e, se a informação puder ter mudado, diga de quando ela é. Humor seco e sutil é bem-vindo, no máximo uma tirada por resposta e nunca "
    "em erros, alertas ou assuntos sérios. Nunca faça o usuário se sentir burro. "
    "Quando algo der errado, assuma com calma e diga o próximo passo, sem desculpas técnicas. "
    "Antes de qualquer ação irreversível, pergunte. "
    "Comece com uma confirmação natural quando o usuário pedir uma ação. Responda apenas ao que foi "
    "pedido. Use as notícias e a imagem da webcam somente quando forem fornecidas, e nunca "
    "invente detalhes que você não enxerga ou que não estejam nas notícias. Se faltar "
    "informação, diga isso de forma breve. Quando perguntarem sobre o próprio usuário, responda "
    "com base no que ele contou sobre si; se não constar lá, diga que ele ainda não lhe contou isso. "
    "O sistema local do JARVIS (não você) cuida de timers e lembretes, anotações, contas, clima, "
    "cotações, abrir sites e programas, pesquisas no navegador, protocolos, arquivos e leitura de tela, "
    "quando o usuário pede de forma direta (por exemplo: 'me avise em 10 minutos', 'anote comprar leite', "
    "'abra o YouTube', 'protocolo trabalho'). Se o usuário pedir algo assim e a mensagem chegar até você, "
    "oriente em uma frase como pedir diretamente. "
    "Você não executa outras ações no computador e nunca deve dizer que fez algo que não fez. "
    # V6.7: bem-estar (escuta ativa; mordomo atento, não terapeuta)
    "Quando o usuário demonstrar cansaço, estresse, tristeza, ansiedade ou desabafar: acolha primeiro "
    "(nomeie o sentimento e valide, sem minimizar), faça no máximo uma pergunta aberta e só depois, se fizer "
    "sentido, ofereça algo prático e curto (respiração guiada, uma pausa, dividir o problema em um primeiro passo, "
    "olhar o pensamento por outro ângulo). Nesses momentos, deixe o humor de lado. Nunca diagnostique, não "
    "rotule e não prometa resultados. Se o mal-estar parecer persistente, sugira com gentileza conversar com um "
    "psicólogo. Se houver qualquer sinal de risco à vida, oriente a ligar para o CVV (188, 24 horas) ou o SAMU (192)."
)

PERSONALITY_PROMPTS = {
    "direto": "Seja objetivo e natural.",
    "descontraido": "Use um tom leve, próximo e bem-humorado, sem exagerar.",
    "formal": "Use um tom profissional, claro e respeitoso.",
    # V6.5.14: como uma assistente de voz (Alexa): curtinho, natural e direto ao ponto
    "alexa": ("Responda como uma assistente de voz de casa (estilo Alexa): no máximo 1 ou 2 frases bem curtas, "
              "a informação primeiro, linguagem do dia a dia, sem rodeios e sem 'senhor' em toda resposta. "
              "Se precisar de mais detalhes, ofereça em uma frase ('Quer que eu detalhe?')."),
}

_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]

# Palavras que indicam que o usuário quer notícias / quer que o JARVIS olhe pela câmera.
NEWS_HINTS = ("notícia", "noticia", "manchete", "jornal", "novidades do dia", "o que aconteceu")
CAMERA_HINTS = ("câmera", "camera", "webcam", "me vê", "me ve", "me veja", "olha", "olhe",
                "como estou", "como eu estou", "o que você vê", "o que voce ve", "está vendo",
                "esta vendo", "minha aparência", "minha aparencia", "me enxerga", "analise o ambiente",
                "analisar o ambiente", "na câmera", "na camera")


def _wants(text: str, hints: tuple) -> bool:
    lowered = text.lower()
    return any(h in lowered for h in hints)


def _build_prompt(user_text: str, *, routine: bool, frame: bool, camera_asked: bool,
                  news: list[dict], news_asked: bool) -> str:
    now = datetime.now()
    lines = [f"Data e hora atuais: {_WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}, {now:%H:%M}."]
    user_name = get_name()
    if user_name:
        lines.append(f"Nome do usuário: {user_name}.")
    about = get_about()
    if about:
        lines.append("O que o usuário contou sobre si mesmo: " + " / ".join(about.splitlines()))
    if routine:
        lines.append(
            "Modo: rotina de saudação. A mensagem do usuário é só o gatilho; cumprimente conforme "
            "o horário real acima, comente de forma gentil algo visível na imagem (se houver) e "
            "resuma os destaques das notícias (se houver)."
        )
    if camera_asked:
        lines.append("Imagem da webcam: anexada (capturada agora)." if frame else "Imagem da webcam: indisponível.")
    if news_asked:
        if news:
            lines.append("Destaques de notícias do dia:")
            lines += [f"- {n['title']} ({n['source']})" if n["source"] else f"- {n['title']}" for n in news]
        else:
            lines.append("Notícias do dia: indisponíveis no momento.")
    lines.append(f'Mensagem do usuário: "{user_text}"')
    context = memory.prompt_context()
    if context:
        lines.append(context)
    return "\n".join(lines)


# Clientes dos provedores reaproveitados entre perguntas (refatoração 4.2): criar um cliente novo a
# cada pergunta refazia a conexão segura (TLS) com o servidor e somava atraso em toda resposta.
_clients: dict[tuple[str, str], object] = {}
_clients_lock = threading.Lock()


def _client(provider: str, api_key: str, factory):
    key = (provider, api_key)
    with _clients_lock:
        client = _clients.get(key)
        if client is None:
            client = factory()
            _clients[key] = client
        return client


def _timeout_s() -> float:
    """V8.11: segundos máximos de cada chamada à IA (LLM_TIMEOUT_S no .env)."""
    try:
        return max(3.0, float(getattr(settings, "LLM_TIMEOUT_S", 25) or 25))
    except (TypeError, ValueError):
        return 25.0


def _image_part(frame_b64: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}}


def _call_openai(prompt: str, frame_b64: Optional[str], history: list[dict]) -> str:
    from openai import OpenAI

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY não configurada no arquivo .env.")

    client = _client("openai", settings.OPENAI_API_KEY, lambda: OpenAI(api_key=settings.OPENAI_API_KEY, timeout=_timeout_s(), max_retries=1))
    content: list[dict] = [{"type": "text", "text": prompt}]
    if frame_b64:
        content.append(_image_part(frame_b64))

    messages = [{"role": "system", "content": _system_text(_tools_var.get())}, *history,
                {"role": "user", "content": content}]
    return _openai_style(client, settings.OPENAI_MODEL, messages, _tools_var.get())


def _openai_style(client, model: str, messages: list[dict], ts: Optional[_ToolSession]) -> str:
    """V8.11: conversa no formato da OpenAI (OpenAI e Groq), com as Skills como funções quando houver."""
    if ts is None or not ts.skills:
        response = client.chat.completions.create(model=model, max_tokens=_max_tokens(), messages=messages)
        return (response.choices[0].message.content or "").strip()
    import json

    from core.skills.llm_adapters import to_openai

    try:
        response = client.chat.completions.create(model=model, max_tokens=_max_tokens(), messages=messages,
                                                  tools=to_openai(ts.skills), tool_choice="auto")
    except Exception as exc:  # noqa: BLE001 - modelo sem suporte a funções: responde sem elas
        if is_quota_error(exc) or _is_timeout(exc):
            raise
        log.warning("IA recusou as funções (%s); respondendo sem elas.", str(exc)[:160])
        plain = [m if m.get("role") != "system" else {"role": "system", "content": SYSTEM_PROMPT} for m in messages]
        response = client.chat.completions.create(model=model, max_tokens=_max_tokens(), messages=plain)
        return (response.choices[0].message.content or "").strip()
    msg = response.choices[0].message
    calls = list(getattr(msg, "tool_calls", None) or [])[:MAX_TOOL_CALLS]
    if not calls:
        return (msg.content or "").strip()
    results = []
    for call in calls:
        try:
            args = json.loads(call.function.arguments or "{}")
        except ValueError:
            args = {}
        results.append(ts.run(call.function.name, args if isinstance(args, dict) else {}))
    spoken = _spoken(results)
    if spoken:
        return spoken
    follow = [*messages, {"role": "assistant", "content": msg.content or "", "tool_calls": [
        {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
        for c in calls]}]
    follow += [{"role": "tool", "tool_call_id": c.id, "content": json.dumps(_tool_payload(r), ensure_ascii=False)}
               for c, r in zip(calls, results)]
    try:
        response = client.chat.completions.create(model=model, max_tokens=_max_tokens(), messages=follow)
        return (response.choices[0].message.content or "").strip() or _after_skills(results)
    except Exception:  # noqa: BLE001 - a ação já rodou: não pode falhar (nem repetir em outra IA)
        log.exception("A IA não montou a frase depois das Skills")
        return _after_skills(results)


_last_grounding_data: dict = {"queries": [], "sources": []}


def get_last_grounding_data() -> dict:
    """Retorna os metadados e fontes da última pesquisa realizada via Google Search Grounding."""
    return dict(_last_grounding_data)


def _call_gemini(prompt: str, frame_b64: Optional[str], history: list[dict], deep: bool = False) -> str:
    """Gemini nativo com Google Search Grounding para perguntas atuais."""
    global _last_grounding_data
    from google import genai
    from google.genai import types

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada no arquivo .env.")

    client = _client("gemini", settings.GEMINI_API_KEY, lambda: genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=int(_timeout_s() * 1000)),  # milissegundos
    ))

    # Constrói o histórico real de conversa (últimas ~10 mensagens)
    contents: list[types.Content] = []
    recent = [
        item for item in history[-10:]
        if isinstance(item.get("content"), str) and item.get("content", "").strip()
    ]
    # Garante que a primeira entrada seja do usuário
    while recent and recent[0].get("role") in {"assistant", "model"}:
        recent.pop(0)

    for item in recent:
        role = "model" if item.get("role") in {"assistant", "model"} else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=item["content"])],
            )
        )

    # Mensagem atual (imagem da câmera, se houver, vai apenas na mensagem atual)
    current_parts = [types.Part.from_text(text=prompt)]
    if frame_b64:
        current_parts.append(types.Part.from_bytes(
            data=base64.b64decode(frame_b64),
            mime_type="image/jpeg",
        ))
    contents.append(types.Content(role="user", parts=current_parts))

    ts = _tools_var.get()
    # A pesquisa do Google e as funções (Skills) não vão juntas na mesma chamada: com pesquisa, nada de Skills
    if deep:
        tools = [types.Tool(google_search=types.GoogleSearch())]
        ts = None
    elif ts is not None and ts.skills:
        from core.skills.llm_adapters import to_gemini

        tools = [to_gemini(ts.skills)]
    else:
        tools, ts = None, None
    system_text = _system_text(ts)
    # a decisão de rodar a skill é do executor (permissão, "sim"), nunca automática dentro da biblioteca
    afc = types.AutomaticFunctionCallingConfig(disable=True)
    max_tokens = max(_max_tokens(), 1000)
    thinking_cfg = types.ThinkingConfig(thinking_budget=0)

    models_to_try = [settings.GEMINI_MODEL]
    for alt in ("gemini-2.5-flash-lite", "gemini-flash-lite-latest"):
        if alt not in models_to_try:
            models_to_try.append(alt)

    response = None
    last_exc = None
    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_text,
                    max_output_tokens=max_tokens,
                    thinking_config=thinking_cfg,
                    tools=tools,
                    automatic_function_calling=afc,
                ),
            )
            break
        except Exception as exc:
            last_exc = exc
            # V8.11: só vale repetir "sem ferramentas" quando havia ferramenta (a pesquisa do Google) e o erro
            # não foi de limite/tempo. Antes eram até 6 chamadas seguidas (3 modelos x 2) num erro qualquer.
            if tools is None or is_quota_error(exc) or _is_timeout(exc):
                log.warning("Modelo %s falhou (%s). Tentando o próximo modelo...", target_model, str(exc)[:160])
                if _is_timeout(exc):
                    break  # o próximo modelo esperaria o mesmo tempo: o modo automático segue para outra IA
                continue
            log.warning("Modelo %s com ferramentas falhou (%s). Tentando sem ferramentas...", target_model, exc)
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=max_tokens,
                        thinking_config=thinking_cfg,
                    ),
                )
                ts = None  # respondeu sem as funções
                break
            except Exception as inner_exc:
                last_exc = inner_exc
                log.warning("Modelo %s também falhou sem ferramentas (%s).", target_model, inner_exc)
                continue

    if not response and last_exc:
        raise last_exc

    # V8.11: a IA pediu Skills (function calling): o executor roda (com as regras de permissão)
    calls = list(getattr(response, "function_calls", None) or [])[:MAX_TOOL_CALLS] if ts is not None else []
    if calls:
        results = [ts.run(fc.name, dict(fc.args or {})) for fc in calls]
        spoken = _spoken(results)
        if spoken:
            _last_grounding_data = {"queries": [], "sources": []}
            return spoken
        follow = list(contents)
        if response.candidates and response.candidates[0].content:
            follow.append(response.candidates[0].content)
        follow.append(types.Content(role="user", parts=[
            types.Part.from_function_response(name=fc.name, response=_tool_payload(r)) for fc, r in zip(calls, results)
        ]))
        try:
            response = client.models.generate_content(
                model=target_model, contents=follow,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, max_output_tokens=max_tokens,
                                                   thinking_config=thinking_cfg),
            )
        except Exception:  # noqa: BLE001 - a ação já rodou: não pode falhar (nem repetir em outra IA)
            log.exception("A IA não montou a frase depois das Skills")
            return _after_skills(results)

    # Extrai metadados de busca (fontes, URLs, títulos)
    queries: list[str] = []
    sources: list[dict] = []
    full_text = ""

    if response.candidates:
        cand = response.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        if gm:
            queries = list(getattr(gm, "web_search_queries", []) or [])
            chunks = getattr(gm, "grounding_chunks", []) or []
            for c in chunks:
                web = getattr(c, "web", None)
                if web:
                    w_title = getattr(web, "title", "") or ""
                    w_uri = getattr(web, "uri", "") or ""
                    if w_uri:
                        sources.append({
                            "name": w_title or "Google Search",
                            "headline": w_title or "Notícia / Fonte Verificada",
                            "url": w_uri,
                        })
        if cand.content and cand.content.parts:
            text_parts = [
                p.text for p in cand.content.parts
                if getattr(p, "text", None) and not getattr(p, "thought", False)
            ]
            full_text = "".join(text_parts).strip()

    _last_grounding_data = {
        "queries": queries,
        "sources": sources,
    }

    if not full_text:
        try:
            full_text = (response.text or "").strip()
        except Exception:
            full_text = ""

    if not full_text and sources:
        full_text = "Com base nas consultas e notícias mais recentes na web, analisei as principais atualizações e reuni os dados essenciais para o senhor."

    return full_text


def _call_anthropic(prompt: str, frame_b64: Optional[str], history: list[dict]) -> str:
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada no arquivo .env.")

    client = _client("anthropic", settings.ANTHROPIC_API_KEY, lambda: anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY, timeout=_timeout_s(), max_retries=1))
    content: list[dict] = []
    if frame_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
        })
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=_max_tokens(),
        system=SYSTEM_PROMPT,
        messages=[*history, {"role": "user", "content": content}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _call_groq(prompt: str, frame_b64: Optional[str], history: list[dict]) -> str:
    """V8.2: Groq (API no formato da OpenAI). Só texto: com imagem da câmera, o automático usa o Gemini."""
    from openai import OpenAI

    key = getattr(settings, "GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY não configurada.")
    if frame_b64:
        raise RuntimeError("A Groq não vê imagens: usando outra IA.")
    client = _client("groq", key, lambda: OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1",
                                                    timeout=_timeout_s(), max_retries=1))
    ts = _tools_var.get()
    messages = [{"role": "system", "content": _system_text(ts)}, *history, {"role": "user", "content": prompt}]
    return _openai_style(client, settings.GROQ_MODEL, messages, ts)


# ------------------------------------------------------------------ V8.2: Automático grátis
# Groq (rápida) é a principal e o Gemini a reserva (o Gemini também é o primeiro quando precisa pesquisar no
# Google). Quando uma chega no limite, fica de lado por um tempo e a outra responde sozinha.
_provider_rest: dict[str, float] = {}
_last_provider = ""
AUTO_ORDER = ("groq", "gemini", "openai", "anthropic")
DAILY_REST = 60 * 60  # limite do dia: deixa a IA de lado por 1 h (depois tenta de novo)
SHORT_REST = 60


def provider_keys() -> dict[str, bool]:
    return {"groq": bool(getattr(settings, "GROQ_API_KEY", "")), "gemini": bool(settings.GEMINI_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY), "anthropic": bool(settings.ANTHROPIC_API_KEY)}


def provider_rest(name: str) -> int:
    """Segundos que esta IA ainda fica de lado por ter chegado no limite (0 = disponível)."""
    return max(0, int(_provider_rest.get(name, 0) - time.time()))


def last_provider() -> str:
    return _last_provider


def _auto_order(deep: bool, frame: bool) -> list[str]:
    keys = provider_keys()
    order = list(AUTO_ORDER)
    if deep or frame:  # pesquisa no Google e imagens: o Gemini sabe fazer
        order.remove("gemini")
        order.insert(0, "gemini")
    usable = [p for p in order if keys[p]]
    ready = [p for p in usable if not provider_rest(p)]
    return ready or usable  # todas de lado? tenta mesmo assim, na ordem


def _call_one(provider: str, prompt: str, frame_b64: Optional[str], history: list[dict], deep: bool) -> str:
    global _last_provider
    if provider == "groq":
        out = _call_groq(prompt, frame_b64, history)
    elif provider == "anthropic":
        out = _call_anthropic(prompt, frame_b64, history)
    elif provider == "openai":
        out = _call_openai(prompt, frame_b64, history)
    elif provider == "gemini":
        out = _call_gemini(prompt, frame_b64, history, deep=deep)
    else:
        raise RuntimeError(f'LLM_PROVIDER inválido: "{provider}". Use "auto", "groq", "openai", "anthropic" ou "gemini".')
    _last_provider = provider
    return out


def _call_auto(prompt: str, frame_b64: Optional[str], history: list[dict], deep: bool) -> str:
    last_exc: Exception | None = None
    for provider in _auto_order(deep, bool(frame_b64)):
        try:
            return _call_one(provider, prompt, frame_b64, history, deep)
        except Exception as exc:  # noqa: BLE001 - tenta a próxima
            last_exc = exc
            ts = _tools_var.get()
            if ts is not None and ts.called:  # V8.11: uma Skill já rodou: outra IA a repetiria
                raise
            if is_quota_error(exc):
                daily = "day" in str(exc).lower() or "dia" in str(exc).lower() or "perday" in str(exc).lower()
                _provider_rest[provider] = time.time() + (DAILY_REST if daily else SHORT_REST)
                log.warning("Automático grátis: %s chegou no limite; usando a próxima IA.", provider)
            else:
                log.warning("Automático grátis: %s falhou (%s); usando a próxima IA.", provider, str(exc)[:120])
    if last_exc is None:
        raise RuntimeError("Nenhuma IA conectada. Conecte a Groq ou o Gemini em Cérebro (IA).")
    raise last_exc


def _call_llm(prompt: str, frame_b64: Optional[str], history: list[dict], deep: bool = False) -> str:
    provider, personality = prefs.get_llm_config()
    prompt = f"{PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS['direto'])}\n{prompt}"
    if provider == "auto":
        return _call_auto(prompt, frame_b64, history, deep)
    if provider == "groq":
        if frame_b64 or (deep and settings.GEMINI_API_KEY):
            return _call_one("gemini", prompt, frame_b64, history, deep) if settings.GEMINI_API_KEY else _call_groq(prompt, None, history)
        return _call_one("groq", prompt, frame_b64, history, deep)
    # Pesquisa na internet (modo automático ou profunda): a busca do Google está ligada só no Gemini.
    # Com outro provedor escolhido, a pergunta que precisa de pesquisa vai para o Gemini, se houver chave.
    if deep and provider != "gemini" and settings.GEMINI_API_KEY:
        return _call_one("gemini", prompt, frame_b64, history, True)
    return _call_one(provider, prompt, frame_b64, history, deep)


def ask_with_provider(prompt: str, provider: str) -> str:
    """V8.2: TESTAR ESTA IA com uma IA específica (ou "auto")."""
    full = f"{PERSONALITY_PROMPTS['direto']}\n{prompt}"
    if provider == "auto":
        return _call_auto(full, None, [], False)
    return _call_one(provider, full, None, [], False)


def ask_with_image(prompt: str, image_b64: str) -> str:
    """Pergunta avulsa com uma imagem JPEG (4.2: leitura de tela). Sem histórico e sem pesquisa web.

    Usa o mesmo provedor e personalidade da conversa; o anexo segue o caminho da imagem da câmera.
    """
    now = datetime.now()
    full = f"Data e hora atuais: {_WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}, {now:%H:%M}.\n{prompt}"
    return (_call_llm(full, image_b64, [], deep=False) or "").strip()


_budget = threading.local()


def _max_tokens() -> int:
    """Limite de resposta: o do .env, ou mais quando a tela pede (V7.13: holograma com animações)."""
    base = int(getattr(settings, "LLM_MAX_TOKENS", 400) or 400)
    return max(base, int(getattr(_budget, "value", 0) or 0))


def ask_text(prompt: str, web: bool = False, max_tokens: int | None = None) -> str:
    """V7.1: pergunta avulsa só com texto (sem histórico, sem câmera), para as telas montadas pela IA.

    V7.8: web=True pesquisa no Google antes de responder (Gemini); as fontes ficam em get_last_grounding_data().
    """
    now = datetime.now()
    full = f"Data e hora atuais: {_WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}, {now:%H:%M}.\n{prompt}"
    _budget.value = max_tokens or 0
    try:
        return (_call_llm(full, None, [], deep=web) or "").strip()
    finally:
        _budget.value = 0


def _tool_session(user_text: str, routine: bool, deep: bool, frame: bool) -> Optional[_ToolSession]:
    """Skills oferecidas à IA neste turno. Fica de fora na rotina, na pesquisa na internet (o conteúdo da web
    não pode induzir ações) e com imagem da câmera."""
    if routine or deep or frame:
        return None
    try:
        from core import voice_route
        from core.skills import registry

        skills = registry.llm_skills()
        if not skills:
            return None
        return _ToolSession(asyncio.get_running_loop(), skills, user_text, get_name() or "", voice_route.current(),
                            voice_route.is_remote())
    except Exception:  # noqa: BLE001 - sem Skills, a conversa segue normal
        log.exception("Não consegui preparar as Skills para a IA")
        return None


async def generate_jarvis_response(
    user_text: str,
    on_step: Optional[StepCallback] = None,
    history: Optional[list[dict]] = None,
    routine: bool = False,
    deep: bool = False,
    web: bool = False,
) -> str:
    """Executa o pipeline e devolve o texto do JARVIS.

    - web=True (modo automático, como a Alexa): a IA pesquisa no Google antes de responder, sem gastar
      a cota da pesquisa profunda.

    - routine=True: rotina completa (câmera + notícias), usada pelo botão "Bom Dia".
    - routine=False: conversa; só usa câmera/notícias se o pedido mencionar (ex.: "notícias de hoje").
    Se câmera ou notícias falharem, o JARVIS segue sem elas.
    """
    history = history or []
    use_news = routine or _wants(user_text, NEWS_HINTS)
    use_camera = routine or _wants(user_text, CAMERA_HINTS)

    async def notify(step: str, status: str) -> None:
        if on_step:
            await on_step(step, status)

    async def get_frame() -> Optional[str]:
        if not use_camera:
            return None
        await notify("camera", "active")
        try:
            frame = await asyncio.to_thread(capture_webcam_frame)
            await notify("camera", "done")
            return frame
        except Exception as exc:  # noqa: BLE001
            log.warning("Câmera indisponível: %s", exc)
            await notify("camera", "error")
            return None

    async def get_news() -> list[dict]:
        if not use_news:
            return []
        await notify("news", "active")
        try:
            news = await asyncio.to_thread(fetch_top_news)
            await notify("news", "done")
            return news
        except Exception as exc:  # noqa: BLE001
            log.warning("Notícias indisponíveis: %s", exc)
            await notify("news", "error")
            return []

    frame, news = await asyncio.gather(get_frame(), get_news())

    prompt = _build_prompt(
        user_text, routine=routine, frame=frame is not None, camera_asked=use_camera,
        news=news, news_asked=use_news,
    )

    ts = _tool_session(user_text, routine=routine, deep=deep or web, frame=frame is not None)
    token = _tools_var.set(ts)
    _skill_cards_var.set([])
    await notify("llm", "active")
    try:
        budget = max(1.0, float(getattr(settings, "LLM_TURN_BUDGET_S", 50) or 50))
        # V8.11: o turno inteiro tem um teto (somando as reservas do modo automático). A thread que ficou
        # esperando a IA termina sozinha depois; o JARVIS já fica livre para o próximo pedido.
        text = await asyncio.wait_for(asyncio.to_thread(_call_llm, prompt, frame, history, deep or web), timeout=budget)
    except asyncio.TimeoutError as exc:
        await notify("llm", "error")
        log.warning("A IA passou de %.0f s sem responder; turno liberado.", budget)
        raise LLMTimeout(f"A inteligência artificial demorou mais de {budget:.0f} segundos para responder.") from exc
    except Exception:
        await notify("llm", "error")
        raise
    finally:
        _tools_var.reset(token)
    await notify("llm", "done")
    if ts is not None and ts.cards:
        _skill_cards_var.set(list(ts.cards))

    if not text:
        if _last_grounding_data.get("sources"):
            text = "Com base nas consultas e notícias mais recentes na web, analisei as principais informações e atualizei os dados no painel tático, senhor."
        else:
            log.warning("Resposta da IA vazia para prompt: %s", prompt[:80])
            text = "Compreendi o seu pedido, senhor. A consulta foi concluída, mas não obtive novos dados adicionais no momento."
    return text
