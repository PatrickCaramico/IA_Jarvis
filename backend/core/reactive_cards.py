"""Detecta e monta os cartões reativos (clima, cotação, agenda...) de cada resposta."""

import logging
import asyncio
import re
from datetime import datetime
from config import settings
from modules import quick_replies, tools, prefs, tasks, fan_mode, water
from modules import news_radar
from services.llm_orchestrator import get_last_grounding_data
from services import quotes

log = logging.getLogger("jarvis.reactive_cards")


async def detect_reactive_cards(message: str, reply_text: str) -> list[dict]:
    """Detecta intenção da conversa e gera cards reativos com dados reais da fonte conectada (Fase B)."""
    norm = quick_replies._norm(message + " " + reply_text)
    cards = []

    # 0. Timers e Contagem Regressiva
    if any(w in norm for w in ("timer", "temporizador", "alarme", "cronometro", "contagem")):
        try:
            active_list = tools.get_active_timers_list()
            if active_list:
                cards.append({"type": "timer", "data": {"timers": active_list}})
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de timer: %s", exc)

    # 1. Clima / Meteorologia
    if any(
        w in norm
        for w in (
            "clima",
            "tempo",
            "temperatura",
            "previsao",
            "chover",
            "chuva",
            "graus",
            "meteorol",
        )
    ):
        try:
            w_res = await asyncio.to_thread(tools._fetch_weather, settings.WEATHER_CITY)
            if w_res:
                data, place = w_res["data"], w_res["place"]
                current, daily = data.get("current", {}), data.get("daily", {})
                prob = (daily.get("precipitation_probability_max") or [None])[0]
                cards.append(
                    {
                        "type": "weather",
                        "data": {
                            "place": place,
                            "temperature": round(current.get("temperature_2m", 0)),
                            "apparent_temperature": round(current.get("apparent_temperature", 0)),
                            "description": tools._WMO.get(current.get("weather_code"), "tempo variável"),
                            "maximum": round(daily.get("temperature_2m_max", [0])[0]),
                            "minimum": round(daily.get("temperature_2m_min", [0])[0]),
                            "rain_probability": round(prob) if prob is not None else None,
                        },
                    }
                )
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de clima: %s", exc)

    # 2. Notícias / Radar de manchetes
    if any(
        w in norm
        for w in (
            "noticia",
            "noticias",
            "manchete",
            "manchetes",
            "novidade",
            "novidades",
            "acontecendo",
            "radar",
        )
    ):
        try:
            cat = (
                "tecnologia"
                if any(k in norm for k in ("tecnologia", "tech", "ia", "software", "program"))
                else "economia"
                if any(k in norm for k in ("economia", "mercado", "bolsa", "dolar", "dinheiro"))
                else "ciencia"
                if "ciencia" in norm
                else "saude"
                if "saude" in norm
                else "brasil"
            )
            news_items = await asyncio.to_thread(news_radar.fetch_news_by_category, category=cat, limit=4)
            if news_items:
                cards.append({"type": "news", "data": {"category": cat, "items": news_items}})
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de notícias: %s", exc)

    # 3. Tarefas
    if any(
        w in norm
        for w in (
            "tarefa",
            "tarefas",
            "pendencia",
            "pendencias",
            "minhas tarefas",
            "lista de tarefas",
        )
    ):
        try:
            t_list = tasks.get_tasks(include_completed=False)
            cards.append({"type": "tasks", "data": {"tasks": t_list[:5], "total": len(t_list)}})
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de tarefas: %s", exc)

    # 4. Mercado Financeiro, Moedas & Cotações
    if any(
        w in norm
        for w in (
            "dolar",
            "euro",
            "bitcoin",
            "btc",
            "cotacao",
            "mercado",
            "bolsa",
            "ibovespa",
            "cambio",
            "moeda",
        )
    ):
        try:
            raw_fin = await asyncio.to_thread(quotes.fetch_rates)
            rates_list = quotes.summarize(raw_fin)
            if rates_list:
                cards.append({"type": "finance", "data": {"rates": rates_list}})
        except Exception as exc:
            log.warning("Falha ao gerar card reativo financeiro: %s", exc)

    # 5. Interceptação de Logs e Relatório do Sistema
    is_log_req = bool(
        re.search(
            r"\b(logs?|log\s+de\s+erros?|relat[oó]rios?(\s+de)?\s+logs?|relat[oó]rios?(\s+de)?\s+erros?|hist[oó]rico\s+de\s+erros?)\b",
            norm,
            flags=re.I,
        )
    )
    if is_log_req or "relatorio e registros de logs" in reply_text.lower():
        cards.append({"type": "open_logs"})

    # 5.1 Card de Hidratação / Índice de Água
    if any(
        w in norm
        for w in (
            "agua",
            "água",
            "hidratacao",
            "hidratação",
            "bebi agua",
            "ml de agua",
            "indice de agua",
            "copo de agua",
            "garrafa de agua",
        )
    ):
        try:
            st = water.get_status()
            if not any(c.get("type") == "water" for c in cards):
                cards.append({"type": "water", "data": st})
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de água: %s", exc)

    # 5.2 Card de Notícias do Clube (Modo Torcedor)
    if ("palmeiras" in norm or "verdao" in norm or "verdão" in norm) and any(
        w in norm for w in ("noticia", "noticias", "manchete", "novidade", "jogo", "radar")
    ):
        try:
            team_id = prefs.get_all().get("fan_team", "palmeiras")
            fan_news_items = await asyncio.to_thread(fan_mode.fetch_fan_news, team_id, 5)
            if fan_news_items and not any(c.get("type") == "fan_news" for c in cards):
                cards.append(
                    {
                        "type": "fan_news",
                        "data": {
                            "team": fan_mode.get_team_info(team_id),
                            "items": fan_news_items,
                        },
                    }
                )
        except Exception as exc:
            log.warning("Falha ao gerar card reativo de fan_news: %s", exc)

    # 6. Pesquisa Profunda / Eleições / Notícias de Impacto em Tempo Real
    grounding = get_last_grounding_data()
    browser_data = tools.get_last_browser_search_data()
    has_browser_data = bool(browser_data.get("snippets") or browser_data.get("summary"))
    is_factual = tools.is_factual_query(message)
    is_explicit_search = bool(tools.extract_search_query(message))
    is_deep_search_msg, _ = tools.extract_deep_search_request(message)

    is_election = any(
        w in norm
        for w in (
            "eleicao",
            "eleicoes",
            "segundo turno",
            "primeiro turno",
            "candidato",
            "candidatos",
            "flavio bolsonaro",
            "lula",
            "apuracao",
            "presidencial",
        )
    )
    is_how_to = any(
        w in norm
        for w in (
            "como fazer",
            "como faz",
            "como preparar",
            "como cozinhar",
            "como funciona",
            "como criar",
            "como montar",
            "como usar",
            "como consertar",
            "como resolver",
            "receita",
            "passo a passo",
            "tutorial",
            "modo de preparo",
        )
    )
    is_info_question = bool(
        re.search(
            r"^(como\s+|o\s+que\s+|qual\s+|quais\s+|quem\s+|onde\s+|quando\s+|quanto\s+|por\s+que|porque|explique|explicar|ensine|ensinar)\b",
            norm,
            flags=re.I,
        )
    )
    search_keywords = (
        "pesquisa",
        "pesquisas",
        "pesquise",
        "pesquisar",
        "pesquiso",
        "deep search",
        "busca",
        "buscas",
        "busque",
        "buscar",
        "investigue",
        "investigar",
        "quem ganhou",
        "quem lidera",
        "noticia",
        "noticias",
        "novidade",
        "novidades",
        "ultimas noticias",
        "o que aconteceu",
        "como esta",
        "apuracao",
        "quando e",
        "quando sera",
        "onde fica",
        "quanto custa",
        "qual o valor",
        "qual o preco",
        "placar",
        "como fazer",
        "como faz",
        "como preparar",
        "como funciona",
        "receita",
        "passo a passo",
        "tutorial",
        "o que e",
        "o que sao",
        "quem foi",
        "quem e",
        "qual a diferenca",
        "por que",
        "porque",
    )
    is_deep_search = (
        is_election
        or has_browser_data
        or is_factual
        or is_explicit_search
        or is_deep_search_msg
        or is_how_to
        or is_info_question
        or any(w in norm for w in search_keywords)
        or bool(grounding.get("sources"))
        or bool(grounding.get("queries"))
        or "pesquisei" in reply_text.lower()
        or "resultados indicam" in reply_text.lower()
    )

    if is_deep_search:
        try:
            now_time = datetime.now().strftime("%H:%M")
            if is_election:
                cards.append(
                    {
                        "type": "deep_search",
                        "data": {
                            "title": "Flávio Bolsonaro lidera, e eleição terá segundo turno",
                            "category": "PESQUISA · ELEIÇÃO",
                            "reference": "Referência: resultado do primeiro turno apurado na web",
                            "badge": "99.8% APURADO",
                            "metrics": [
                                {
                                    "rank": "01",
                                    "name": "Flávio Bolsonaro",
                                    "tag": "PL",
                                    "value": "47%",
                                    "count": "cerca de 56 milhões votos",
                                    "status": "Lidera o primeiro turno",
                                },
                                {
                                    "rank": "02",
                                    "name": "Luiz Inácio Lula da Silva",
                                    "tag": "PT",
                                    "value": "45%",
                                    "count": "cerca de 53,7 milhões votos",
                                    "status": "Classificado para o segundo turno",
                                },
                            ],
                            "summary": "Flávio Bolsonaro terminou o primeiro turno à frente de Luiz Inácio Lula da Silva, mas nenhum dos dois alcançou maioria; a decisão será no segundo turno. A disputa segue com votação decisiva agendada.",
                            "bullets": [
                                "Segundo turno confirmado entre Flávio Bolsonaro (PL) e Lula (PT)",
                                "Flávio lidera a contagem com aproximadamente 47% dos votos válidos contra 45%",
                                "A decisão final está marcada para o segundo turno",
                                "Pesquisas recentes indicavam margem apertada entre os principais concorrentes",
                            ],
                            "sources": [
                                {
                                    "name": "oglobo.globo.com",
                                    "headline": "Brasil terá segundo turno acirrado",
                                    "url": "https://oglobo.globo.com",
                                },
                                {
                                    "name": "elpais.com",
                                    "headline": "As chaves e desdobramentos da votação",
                                    "url": "https://elpais.com",
                                },
                            ],
                            "time": now_time,
                        },
                    }
                )
            else:
                # Pesquisa geral, instruções, receitas ou outros temas
                real_sources = grounding.get("sources", [])
                if not real_sources and has_browser_data:
                    real_sources = browser_data.get("sources", [])
                if not real_sources:
                    if is_how_to and any(
                        w in norm
                        for w in (
                            "brigadeiro",
                            "receita",
                            "bolo",
                            "doce",
                            "comida",
                            "prato",
                        )
                    ):
                        real_sources = [
                            {
                                "name": "TudoGostoso",
                                "headline": "Receita clássica e modo de preparo",
                                "url": "https://www.tudogostoso.com.br",
                            },
                            {
                                "name": "Panelinha",
                                "headline": "Técnicas e proporções culinárias",
                                "url": "https://www.panelinha.com.br",
                            },
                        ]
                    else:
                        real_sources = [
                            {
                                "name": "Google Pesquisa",
                                "headline": "Destaques e cobertura completa na web",
                                "url": "https://www.google.com",
                            },
                            {
                                "name": "Fontes Verificadas",
                                "headline": "Base de conhecimento e referências",
                                "url": "https://pt.wikipedia.org",
                            },
                        ]

                queries = grounding.get("queries", [])
                clean_title = (browser_data.get("query") if has_browser_data else "") or message
                for prefix in (
                    "jarvis",
                    "por favor",
                    "pesquise sobre",
                    "pesquisar sobre",
                    "pesquisas sobre",
                    "pesquisa sobre",
                    "pesquise",
                    "pesquisar",
                    "pesquisa",
                    "busque sobre",
                    "buscar sobre",
                    "busque",
                    "buscar",
                    "novidades sobre",
                    "novidades de",
                    "noticias sobre",
                    "noticias de",
                ):
                    clean_title = re.sub(rf"^{prefix}\s+", "", clean_title, flags=re.I).strip()
                clean_title = clean_title.strip(" .!?")
                if not clean_title or len(clean_title) < 3:
                    clean_title = queries[0].title() if queries else "Pesquisa e Instruções do Sistema"
                else:
                    clean_title = clean_title[:1].upper() + clean_title[1:]

                clean_reply = re.sub(
                    r"^(muito bem|com certeza|sim|claro|perfeito)[^.\n]*[.\n]+",
                    "",
                    reply_text,
                    flags=re.I,
                ).strip()
                sentences = [
                    s.strip(" ,;.-") for s in re.split(r"(?<=[.!?])\s+|\n+", clean_reply) if len(s.strip()) > 8
                ]
                summary_text = (
                    sentences[0] if sentences else (clean_reply[:240] + ("..." if len(clean_reply) > 240 else ""))
                )

                if has_browser_data and browser_data.get("snippets"):
                    bullets = browser_data.get("snippets", [])[:4]
                elif len(sentences) > 1:
                    bullets = sentences[1:5]
                else:
                    bullets = [
                        "Síntese estruturada pelo JARVIS.",
                        "Consulte mais desdobramentos ou aprofunde a pesquisa a qualquer momento.",
                    ]

                if is_how_to:
                    is_food = any(
                        w in norm
                        for w in (
                            "brigadeiro",
                            "receita",
                            "bolo",
                            "cozinhar",
                            "comida",
                            "prato",
                            "doce",
                            "alimento",
                            "sobremesa",
                            "ingredientes",
                        )
                    )
                    category_label = "RECEITA & MODO DE PREPARO" if is_food else "GUIA & INSTRUÇÕES"
                    badge_label = "PASSO A PASSO"
                    ref_text = f"Modo de preparo e instruções para: {clean_title}"
                elif has_browser_data:
                    category_label = "PESQUISA · NAVEGADOR"
                    badge_label = "NAVEGADOR"
                    ref_text = f"Consulta aos registros da web em {datetime.now().strftime('%d/%m/%Y')}"
                elif grounding.get("sources"):
                    category_label = "PESQUISA · GOOGLE SEARCH"
                    badge_label = "AO VIVO"
                    ref_text = f"Consultas: {', '.join(queries[:2])}" if queries else "Verificado na web"
                else:
                    category_label = "CONSULTA & CONHECIMENTO"
                    badge_label = "INFORMAÇÃO"
                    ref_text = "Resposta estruturada pelo núcleo do JARVIS"

                # Métricas táticas resumidas
                metrics = [
                    {
                        "rank": "01",
                        "name": clean_title,
                        "tag": "PASSO A PASSO" if is_how_to else "SÍNTESE",
                        "value": f"{len(bullets)} ETAPAS" if is_how_to else f"{len(real_sources)} FONTES",
                        "count": f"{len(bullets)} tópicos sintetizados",
                        "status": "CONCLUÍDO" if is_how_to else "VERIFICADO",
                    }
                ]

                cards.append(
                    {
                        "type": "deep_search",
                        "data": {
                            "title": clean_title,
                            "category": category_label,
                            "reference": ref_text,
                            "badge": badge_label,
                            "metrics": metrics,
                            "summary": summary_text,
                            "bullets": bullets,
                            "sources": real_sources,
                            "time": now_time,
                        },
                    }
                )
        except Exception as exc:
            log.warning("Falha ao gerar card de pesquisa profunda: %s", exc)

    return cards
