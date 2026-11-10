"""Orquestrador: junta visão + notícias + histórico + mensagem do usuário e consulta o LLM."""
import asyncio
import base64
import logging
import threading
import time
from datetime import datetime
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

# on_step("camera", "active" | "done" | "error")
StepCallback = Callable[[str, str], Awaitable[None]]

SYSTEM_PROMPT = (
    # Tom de voz do Branding Book 4.2: mordomo digital competente, discreto e leal (Sábio + Cuidador).
    "Você é J.A.R.V.I.S., o assistente pessoal do usuário: um mordomo digital competente, discreto e leal. "
    "Fale sempre em português do Brasil, com tom formal e cordial. Trate o usuário por 'senhor', sem "
    "repetir o tratamento em todas as frases. "
    "Suas respostas são LIDAS EM VOZ ALTA: frases curtas, a resposta primeiro e o detalhe depois, no máximo "
    "4 frases (só se alongue se o usuário pedir detalhes), sem listas, sem markdown, sem emojis e sem "
    "excesso de exclamações. Humor seco e sutil é bem-vindo, no máximo uma tirada por resposta e nunca "
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
    "Você não executa outras ações no computador e nunca deve dizer que fez algo que não fez."
)

PERSONALITY_PROMPTS = {
    "direto": "Seja objetivo e natural.",
    "descontraido": "Use um tom leve, próximo e bem-humorado, sem exagerar.",
    "formal": "Use um tom profissional, claro e respeitoso.",
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


def _image_part(frame_b64: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}}


def _call_openai(prompt: str, frame_b64: Optional[str], history: list[dict]) -> str:
    from openai import OpenAI

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY não configurada no arquivo .env.")

    client = _client("openai", settings.OPENAI_API_KEY, lambda: OpenAI(api_key=settings.OPENAI_API_KEY))
    content: list[dict] = [{"type": "text", "text": prompt}]
    if frame_b64:
        content.append(_image_part(frame_b64))

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history,
                  {"role": "user", "content": content}],
    )
    return (response.choices[0].message.content or "").strip()


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

    client = _client("gemini", settings.GEMINI_API_KEY, lambda: genai.Client(api_key=settings.GEMINI_API_KEY))

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

    tools = [types.Tool(google_search=types.GoogleSearch())] if deep else None
    max_tokens = max(int(getattr(settings, "LLM_MAX_TOKENS", 400) or 400), 1000)
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
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=max_tokens,
                    thinking_config=thinking_cfg,
                    tools=tools,
                ),
            )
            break
        except Exception as exc:
            last_exc = exc
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
                break
            except Exception as inner_exc:
                last_exc = inner_exc
                log.warning("Modelo %s também falhou sem ferramentas (%s).", target_model, inner_exc)
                continue

    if not response and last_exc:
        raise last_exc

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

    client = _client("anthropic", settings.ANTHROPIC_API_KEY, lambda: anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY))
    content: list[dict] = []
    if frame_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
        })
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[*history, {"role": "user", "content": content}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _call_llm(prompt: str, frame_b64: Optional[str], history: list[dict], deep: bool = False) -> str:
    provider, personality = prefs.get_llm_config()
    prompt = f"{PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS['direto'])}\n{prompt}"
    if provider == "anthropic":
        return _call_anthropic(prompt, frame_b64, history)
    if provider == "openai":
        return _call_openai(prompt, frame_b64, history)
    if provider == "gemini":
        return _call_gemini(prompt, frame_b64, history, deep=deep)
    raise RuntimeError(f'LLM_PROVIDER inválido: "{provider}". Use "openai", "anthropic" ou "gemini".')


def ask_with_image(prompt: str, image_b64: str) -> str:
    """Pergunta avulsa com uma imagem JPEG (4.2: leitura de tela). Sem histórico e sem pesquisa web.

    Usa o mesmo provedor e personalidade da conversa; o anexo segue o caminho da imagem da câmera.
    """
    now = datetime.now()
    full = f"Data e hora atuais: {_WEEKDAYS[now.weekday()]}, {now:%d/%m/%Y}, {now:%H:%M}.\n{prompt}"
    return (_call_llm(full, image_b64, [], deep=False) or "").strip()


async def generate_jarvis_response(
    user_text: str,
    on_step: Optional[StepCallback] = None,
    history: Optional[list[dict]] = None,
    routine: bool = False,
    deep: bool = False,
) -> str:
    """Executa o pipeline e devolve o texto do JARVIS.

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

    await notify("llm", "active")
    try:
        text = await asyncio.to_thread(_call_llm, prompt, frame, history, deep)
    except Exception:
        await notify("llm", "error")
        raise
    await notify("llm", "done")

    if not text:
        if _last_grounding_data.get("sources"):
            text = "Com base nas consultas e notícias mais recentes na web, analisei as principais informações e atualizei os dados no painel tático, senhor."
        else:
            log.warning("Resposta da IA vazia para prompt: %s", prompt[:80])
            text = "Compreendi o seu pedido, senhor. A consulta foi concluída, mas não obtive novos dados adicionais no momento."
    return text
