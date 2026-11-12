"""Motor de conversa: processa cada turno (comandos locais, LLM, busca) e o modo restrito."""

import logging
import asyncio
import re
from datetime import datetime
from fastapi import HTTPException
from modules import (
    face,
    quick_replies,
    tools,
    prefs,
    briefing,
    memory,
    event_log,
    deep_search_quota,
    fan_mode,
    sports_provider,
    water,
    alarms,
)
from modules import access, lock_log, sentinel
from services.llm_orchestrator import (
    generate_jarvis_response,
    get_quota_cooldown,
    set_quota_cooldown,
    is_quota_error,
)
from core import briefing_flow, confirm, runtime, session, speech, reactive_cards

log = logging.getLogger("jarvis.turns")


MAX_HISTORY = 12  # mensagens lembradas na conversa


JARVIS_LOCK_CMD = re.compile(
    r"^(?:jarvis\s+)?(?:(?:pode\s+)?(?:bloquear|bloqueie|bloqueia|trancar|tranque|tranca)(?:\s+(?:o|a)?\s*(?:jarvis|central|sistema|sessao))?"
    # V6.5.7: "ativa o modo bloqueio", "entra no modo de bloqueio", "liga o modo sentinela"...
    r"|(?:(?:pode\s+)?(?:ativar|ativa|ative|entrar|entra|entre|ligar|liga|ligue|coloca|coloque|colocar|vai|ir|vamos)"
    r"(?:\s+(?:o|a|em|no|na|pro|pra|para|para\s+o))*\s+)?modo\s+(?:de\s+)?(?:sentinela|bloqueio|bloqueado)"
    # "volta pra tela de bloqueio", "tela de bloqueio"
    r"|(?:(?:volta|voltar|volte|vai|ir|vamos)(?:\s+(?:pra|para|a|na|pro))*\s+)?(?:a\s+)?tela\s+de\s+bloqueio)$"
)


async def handle_restricted_turn(message: str) -> dict:
    """Central bloqueada (Sentinela) ou modo visitante: só pedidos públicos são executados.

    Não usa a IA, não grava histórico nem memória. Pedidos protegidos devolvem
    requires_unlock=True para a tela pedir o escaneamento facial (o pedido fica pendente no frontend).
    """
    if session.busy:
        raise HTTPException(status_code=409, detail="O JARVIS já está ocupado com outra solicitação.")
    state = access.effective_state()
    session.busy = True
    try:
        wake_words = prefs.get_all().get("sentinel_wake_words") or None
        ai_name = quick_replies._norm(prefs.get_ai_name() or "")
        if wake_words is not None and ai_name and ai_name not in wake_words:
            wake_words = [*wake_words, ai_name]
        result = await sentinel.classify_and_answer(message, state, wake_words)
    except Exception:  # noqa: BLE001
        session.busy = False
        log.exception("Falha ao responder no modo bloqueado")
        raise HTTPException(status_code=500, detail="Não consegui responder agora.")
    reply = result["reply"]
    event_log.add(
        "command",
        "[bloqueado] pedido " + ("público" if result["public"] else "protegido"),
    )
    await runtime.manager.broadcast(
        {
            "type": "sentinel_reply",
            "text": reply,
            "question": message,
            "card": result.get("card"),  # V6.5.8: mini janela da resposta
            "requires_unlock": result["requires_unlock"],
            "access": state,
        }
    )
    runtime.track(speech.speak(reply))
    return {
        "status": "ok",
        "response": reply,
        "cards": [],
        "source": "sentinel",
        "access": state,
        "public": result["public"],
        "requires_unlock": result["requires_unlock"],
        "action": result.get("action"),
        "card": result.get("card"),
    }


async def handle_turn(message: str, routine: bool, force_deep: bool = False) -> dict:
    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    # V5.1: alarme tocando: "parar" / "soneca" valem até com a central bloqueada
    if alarms.is_ringing():
        alarm_reply = await alarms.handle_ringing_voice(quick_replies._norm(message))
        if alarm_reply:
            await runtime.manager.broadcast({"type": "response", "text": alarm_reply, "cards": [], "local": True})
            runtime.track(speech.speak(alarm_reply))
            return {"status": "ok", "response": alarm_reply, "cards": [], "source": "alarm"}
    if access.is_restricted():
        return await handle_restricted_turn(message)
    event_log.add("command", message)
    if session.busy:
        raise HTTPException(status_code=409, detail="O JARVIS já está ocupado com outra solicitação.")
    session.busy = True
    turn = session.turn_id
    name = face.get_name()

    async def finish_local(reply: str, extra_cards: list | None = None) -> dict:
        """Resposta pronta (sem IA): mostra, guarda no histórico e fala."""
        cards = await reactive_cards.detect_reactive_cards(message, reply)
        if extra_cards:
            # O cartão explícito da ação (ex.: água com open_panel) substitui o detectado automaticamente
            extra_types = {c.get("type") for c in extra_cards}
            cards = [c for c in cards if c.get("type") not in extra_types] + list(extra_cards)
        session.history.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
        )
        memory.add_conversation(message, reply)
        del session.history[:-MAX_HISTORY]
        await runtime.manager.broadcast({"type": "reset"})
        await runtime.manager.broadcast({"type": "response", "text": reply, "cards": cards, "local": True})
        runtime.track(speech.speak(reply))
        return {"status": "ok", "response": reply, "cards": cards, "source": "local"}

    # 4.2: resposta a uma ação pendente (sugestão da rotina, organizar pasta)
    if confirm.pending():
        confirm_reply = await confirm.answer(quick_replies._norm(message))
        if confirm_reply:
            return await finish_local(confirm_reply)

    # Resposta a confirmação pendente de pesquisa profunda
    norm_clean = re.sub(r"[^\w\s]", "", message.lower()).strip()
    if session.pending_deep_search_query:
        if norm_clean in {
            "sim",
            "pode liberar",
            "libere",
            "pode usar",
            "confirmo",
            "positivo",
            "claro",
            "com certeza",
            "pode",
            "autorizo",
        }:
            target_query = session.pending_deep_search_query
            session.pending_deep_search_query = None
            can_run, reason = deep_search_quota.can_consume()
            if not can_run:
                return await finish_local(reason)
            deep_search_quota.consume()
            force_deep = True
            message = f"pesquisa profunda sobre {target_query}"
        elif norm_clean in {
            "nao",
            "não",
            "cancela",
            "cancelar",
            "deixa",
            "deixa pra la",
            "negativo",
            "recuso",
        }:
            session.pending_deep_search_query = None
            return await finish_local("Pesquisa profunda cancelada, senhor.")

    # Comandos de sistema: modo silencioso, repita e mais detalhes
    norm_cmd = quick_replies._norm(message)

    # Modo Sentinela: "Jarvis, bloquear" volta para a tela de bloqueio (não confundir com
    # "bloquear a tela", que bloqueia o Windows em system_control).
    if JARVIS_LOCK_CMD.fullmatch(norm_cmd) and access.enforcement_active():
        access.lock("voice")
        lock_log.add("voice", "lock")
        await speech.broadcast_access()
        if "sentinela" in norm_cmd:
            return await finish_local("Bloqueando, senhor. Modo sentinela ativo.")
        return await finish_local("Bloqueando a central, senhor. Até logo.")
    if norm_cmd in {
        "modo silencioso",
        "ativar modo silencioso",
        "ative o modo silencioso",
        "silencio",
        "entrar em modo silencioso",
    }:
        prefs.set_silent_mode(True)
        return await finish_local("Modo silencioso ativado, senhor. As respostas por voz estão silenciadas.")
    if norm_cmd in {
        "desativar modo silencioso",
        "desative o modo silencioso",
        "sair do modo silencioso",
        "desativar silencio",
        "modo normal",
    }:
        prefs.set_silent_mode(False)
        return await finish_local("Modo silencioso desativado, senhor. Respostas em áudio reativadas.")

    if norm_cmd in {
        "modo torcedor",
        "ativar modo torcedor",
        "ative o modo torcedor",
        "ligar modo torcedor",
        "modo palmeiras",
    }:
        prefs.update({"fan_mode_enabled": True})
        team_id = prefs.get_all().get("fan_team", "palmeiras")
        fan_news_items = await asyncio.to_thread(fan_mode.fetch_fan_news, team_id, 5)
        await asyncio.to_thread(sports_provider.refresh, team_id)
        match_info = sports_provider.get_current_or_next_match(team_id)
        sports_provider.record_manual_activation(True, team_id, match_info)

        extra_cards = []
        if fan_news_items:
            extra_cards.append(
                {
                    "type": "fan_news",
                    "data": {
                        "team": fan_mode.get_team_info(team_id),
                        "items": fan_news_items,
                    },
                }
            )
        if match_info:
            extra_cards.append(
                {
                    "type": "fan_score",
                    "data": {
                        "team": fan_mode.get_team_info(team_id),
                        "match": match_info,
                    },
                }
            )

        # Monta a narração falada das 3 primeiras notícias
        news_titles = [it.get("title", "").strip() for it in fan_news_items[:3] if it.get("title")]
        news_speech = ""
        if news_titles:
            ordinals = ["Primeira", "Segunda", "Terceira"]
            parts = [f"{ordinals[i]}: {t}" for i, t in enumerate(news_titles)]
            news_speech = " As três primeiras notícias do Verdão são: " + ". ".join(parts) + "."

        if match_info and match_info.get("is_match_day"):
            hora_str = ""
            if match_info.get("time_known", True):
                try:
                    hora_str = " às " + datetime.fromisoformat(match_info.get("date", "")).strftime("%H:%M")
                except Exception:
                    hora_str = ""
            reply = f"Avante Palestra! Hoje tem jogo do Palmeiras contra o {match_info.get('opponent')}{hora_str}!{news_speech} Bora Palmeiras!"
        else:
            reply = f"Modo torcedor ativado, senhor.{news_speech} Bora Palmeiras!"

        await runtime.manager.broadcast(
            {
                "type": "prefs_updated",
                "fan_mode_enabled": True,
                "fan_team": team_id,
                "is_match_day": match_info.get("is_match_day", False) if match_info else False,
            }
        )
        return await finish_local(reply, extra_cards=extra_cards)

    if norm_cmd in {
        "desativar modo torcedor",
        "desative o modo torcedor",
        "sair do modo torcedor",
        "desligar modo torcedor",
    }:
        prefs.update({"fan_mode_enabled": False})
        sports_provider.record_manual_activation(False, prefs.get_all().get("fan_team", "palmeiras"))
        await runtime.manager.broadcast({"type": "prefs_updated", "fan_mode_enabled": False})
        return await finish_local("Modo torcedor desativado, senhor. Retornando ao layout padrão.")

    if any(
        q in norm_cmd
        for q in (
            "noticias do palmeiras",
            "noticia do palmeiras",
            "noticias do verdao",
            "noticias do verdão",
            "ultimas do palmeiras",
            "ultimas noticias do palmeiras",
            "radar do palmeiras",
            "noticias do time",
            "novidades do palmeiras",
            "verdao noticias",
            "verdão noticias",
            "noticias palmeiras",
        )
    ):
        team_id = prefs.get_all().get("fan_team", "palmeiras")
        fan_news_items = await asyncio.to_thread(fan_mode.fetch_fan_news, team_id, 5)
        extra_cards = [
            {
                "type": "fan_news",
                "data": {
                    "team": fan_mode.get_team_info(team_id),
                    "items": fan_news_items,
                },
            }
        ]
        news_titles = [it.get("title", "").strip() for it in fan_news_items[:3] if it.get("title")]
        if news_titles:
            ordinals = ["Primeira", "Segunda", "Terceira"]
            parts = [f"{ordinals[i]}: {t}" for i, t in enumerate(news_titles)]
            speech_body = ". ".join(parts)
            reply = f"Aqui estão as notícias recentes do Palmeiras no GE, senhor: {speech_body}. Bora Palmeiras!"
        else:
            reply = "Aqui estão as notícias recentes do Palmeiras no GE, senhor. Bora Palmeiras!"
        return await finish_local(reply, extra_cards=extra_cards)

    if any(
        q in norm_cmd
        for q in (
            "agendar jogo",
            "lembrar do jogo",
            "lembrete do jogo",
            "agendar jogo do palmeiras",
            "lembrar jogo do palmeiras",
            "calendario de jogos",
            "agenda de jogos",
            "proximos jogos do palmeiras",
            "proximos jogos",
        )
    ):
        team_id = prefs.get_all().get("fan_team", "palmeiras")
        await asyncio.to_thread(sports_provider.refresh, team_id)
        sched = sports_provider.get_schedule(team_id)
        rem_res = sports_provider.create_match_reminder(None)
        extra_cards = [
            {
                "type": "fan_score",
                "data": {
                    "team": fan_mode.get_team_info(team_id),
                    "match": sports_provider.get_current_or_next_match(team_id),
                    "schedule": sched,
                },
            }
        ]
        if rem_res.get("status") != "ok":
            reply = rem_res.get("message", "Ainda não tenho a agenda dos próximos jogos, senhor.")
        else:
            m = rem_res["match"]
            reply = (
                f"Lembrete agendado para {m['opponent']}, {m.get('competition', '')}, em {m.get('date_human', '')}. "
                "Também deixei o link do Google Agenda no card. Bora Palmeiras!"
            )
        return await finish_local(reply, extra_cards=extra_cards)

    # Comandos de Hidratação / Água (Fase W)
    water_cmd = water.parse_water_command(message)
    if water_cmd:
        action, value = water_cmd
        if action == "query":
            st = water.get_status()
            reply = water.status_sentence(st)
            return await finish_local(reply, extra_cards=[{"type": "water", "data": st, "open_panel": True}])
        if action == "add":
            st = water.add_intake(value)
            reply = f"Registrado: +{value} ml de água! " + water.status_sentence(st)
            if st["goal_reached"] and st["total_ml"] - value < st["goal_ml"]:
                reply += " Meta de água do dia batida, senhor. Bom trabalho."
            await runtime.manager.broadcast({"type": "water_updated", "data": st, "added_ml": value})
            return await finish_local(reply, extra_cards=[{"type": "water", "data": st, "open_panel": True}])
        if action == "set_goal":
            st = water.set_goal(value)
            await runtime.manager.broadcast({"type": "water_updated", "data": st})
            return await finish_local(
                f"Meta diária de hidratação atualizada para {value} ml.",
                extra_cards=[{"type": "water", "data": st}],
            )

    if norm_cmd in {
        "repita",
        "repete",
        "o que voce disse",
        "o que voce falou",
        "pode repetir",
        "repita por favor",
        "repita a resposta",
        "repita o que disse",
    }:
        last_assistant_turn = next(
            (h["content"] for h in reversed(session.history) if h.get("role") == "assistant"),
            None,
        )
        if last_assistant_turn:
            return await finish_local(f"Eu disse: {last_assistant_turn}")
        return await finish_local("Ainda não disse nada para repetir, senhor.")

    if norm_cmd in {
        "mais detalhes",
        "detalhe mais",
        "me de mais detalhes",
        "explique melhor",
        "explique mais",
        "quero mais detalhes",
        "aprofundar",
    }:
        last_assistant_turn = next(
            (h["content"] for h in reversed(session.history) if h.get("role") == "assistant"),
            None,
        )
        if last_assistant_turn:
            message = (
                f"Por favor, detalhe com mais profundidade e explique melhor o seguinte ponto: {last_assistant_turn}"
            )
        else:
            return await finish_local("Sobre qual assunto deseja mais detalhes, senhor?")

    # V4.3: "bom dia" (ou a rotina do botão) dispara o briefing em etapas, um card por assunto;
    # "boa noite" dispara o fechamento do dia no mesmo formato.
    # Vem antes das respostas instantâneas; frases longas ("bom dia, abre o spotify") seguem o fluxo normal.
    mode = briefing.routine_mode() if routine else (briefing.request_mode(norm_cmd) if len(norm_cmd.split()) <= 6 else None)
    if mode and not force_deep:
        await runtime.manager.broadcast({"type": "reset"})
        await runtime.manager.broadcast({"type": "state", "state": "processing"})
        try:
            return await briefing_flow.start(message, turn, MAX_HISTORY, mode)
        except Exception:  # noqa: BLE001
            log.exception("Falha ao montar o briefing em etapas")
            if mode.startswith("topic:"):
                return await finish_local("Não consegui montar essa tela agora, senhor.")
            return await finish_local(await briefing.text_for(mode)())

    # 1) Respostas instantâneas (cumprimentos, "quem te criou?", hora...)
    quick = quick_replies.match(message, name)
    if quick and not force_deep:
        return await finish_local(quick)

    await runtime.manager.broadcast({"type": "reset"})
    await runtime.manager.broadcast({"type": "state", "state": "processing"})

    # Verificação de solicitação explícita de pesquisa profunda
    is_deep_req, deep_q = tools.extract_deep_search_request(message)
    if is_deep_req and not force_deep:
        target_theme = deep_q or session.last_search_query
        if not target_theme:
            return await finish_local("Sobre qual tema deseja realizar a pesquisa profunda, senhor?")
        all_prefs = prefs.get_all()
        if not all_prefs.get("deep_search_allowed", False):
            session.pending_deep_search_query = target_theme
            return await finish_local("A pesquisa profunda está desligada, senhor. Quer liberar só desta vez?")
        can_run, reason = deep_search_quota.can_consume()
        if not can_run:
            return await finish_local(reason)
        deep_search_quota.consume()
        force_deep = True
        message = f"pesquisa profunda sobre {target_theme}"

    web_search = False  # modo automático: a IA pesquisa no Google antes de responder
    # 3) Funções locais (só executa se não for force_deep)
    if not force_deep:
        try:
            tool_reply = await tools.run(message, name)
        except Exception as exc:  # noqa: BLE001
            session.busy = False
            log.exception("Falha ao executar ferramenta local")
            event_log.add(
                "error",
                "Falha ao executar ação local",
                f"Comando: {message}\nDetalhes: {exc}",
            )
            await runtime.manager.broadcast({"type": "error", "message": str(exc)})
            await runtime.manager.broadcast({"type": "state", "state": "idle"})
            runtime.track(
                speech.say_quietly("Senhor, encontrei um problema ao executar essa ação. O erro foi registrado.")
            )
            raise HTTPException(status_code=500, detail="Não foi possível executar essa ação.") from exc
        if speech.canceled(turn):
            return {"status": "canceled"}
        if tool_reply:
            if "Não consegui ler os resultados, senhor. Quer que eu use a pesquisa profunda?" in tool_reply:
                session.pending_deep_search_query = tools.extract_search_query(message) or message
            return await finish_local(tool_reply)

        current_search_mode = prefs.get_search_mode()

        # 4a) Modo automático (como a Alexa): pergunta factual vai para a IA com busca no Google,
        # sem abrir o navegador, sem perguntar e sem gastar a cota da pesquisa profunda.
        if current_search_mode == "auto" and tools.is_factual_query(message):
            web_search = True
            session.last_search_query = re.sub(
                r"^(?:jarvis[\s,]+)?(?:por favor[\s,]+)?", "", message, flags=re.I
            ).strip(" .!?") or message

        # 4) Pergunta factual direcionada ao navegador por padrão (sem gastar cota de API)
        if current_search_mode == "browser" and tools.is_factual_query(message):
            clean_q = re.sub(r"^(?:jarvis[\s,]+)?(?:por favor[\s,]+)?", "", message, flags=re.I).strip(" .!?")
            if clean_q:
                session.last_search_query = clean_q
                browser_reply = await tools.execute_browser_search(clean_q)
                if "Não consegui ler os resultados, senhor. Quer que eu use a pesquisa profunda?" in browser_reply:
                    session.pending_deep_search_query = clean_q
                return await finish_local(browser_reply)

        # 2.1) Pergunta de modo de busca se o modo for "ask" e a mensagem for pesquisa explícita ou factual
        search_query = tools.extract_search_query(message)
        if not search_query and tools.is_factual_query(message):
            search_query = re.sub(r"^(?:jarvis[\s,]+)?(?:por favor[\s,]+)?", "", message, flags=re.I).strip(" .!?")

        if search_query and current_search_mode == "ask":  # no "auto" a pesquisa segue direto para a IA
            prompt_reply = "Como prefere realizar esta pesquisa, senhor? Pela API do Gemini ou no navegador local?"
            prompt_cards = [
                {
                    "type": "search_mode_prompt",
                    "data": {
                        "query": search_query,
                        "message": message,
                        "default_mode": prefs.get_default_search_mode(),
                        "timeout_seconds": 10,
                    },
                }
            ]
            session.history.extend(
                [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": prompt_reply},
                ]
            )
            memory.add_conversation(message, prompt_reply)
            del session.history[:-MAX_HISTORY]
            await runtime.manager.broadcast({"type": "reset"})
            await runtime.manager.broadcast({"type": "response", "text": prompt_reply, "cards": prompt_cards})
            runtime.track(speech.speak(prompt_reply))
            return {
                "status": "ok",
                "response": prompt_reply,
                "cards": prompt_cards,
                "action": "ask_search_mode",
            }

    # 3) IA
    async def on_step(step: str, status: str) -> None:
        await runtime.manager.broadcast({"type": "step", "step": step, "status": status})

    # Verifica se a IA está em período de cooldown (erro 429) antes de chamar a API
    in_cooldown, remaining = get_quota_cooldown()
    if in_cooldown:
        session.busy = False
        cooldown_msg = (
            f"Senhor, a API da inteligência artificial ainda está em resfriamento temporário. "
            f"Restam cerca de {remaining} segundos. Os comandos locais continuam funcionando normalmente."
        )
        return await finish_local(cooldown_msg)

    stop = asyncio.Event()
    session.current_stop = stop
    runtime.track(speech.filler_loop(stop))

    try:
        text = await generate_jarvis_response(
            message,
            on_step,
            history=list(session.history),
            routine=routine,
            deep=force_deep,
            web=web_search,
        )
    except Exception as exc:  # noqa: BLE001
        stop.set()
        if force_deep:
            deep_search_quota.refund()
        if speech.canceled(turn):
            return {"status": "canceled"}
        session.busy = False

        if is_quota_error(exc):
            set_quota_cooldown(60)
            log.warning("Cota da API atingida (429/ResourceExhausted). Cooldown de 60s ativado.")
            quota_msg = (
                "Senhor, a cota da API da inteligência artificial foi atingida temporariamente. "
                "Por favor, aguarde cerca de um minuto antes de fazer uma nova pergunta complexa."
            )
            event_log.add(
                "warning",
                "Cota de API Atingida (429)",
                f"Cooldown de 60s ativado. Detalhes: {exc}",
            )
            return await finish_local(quota_msg)

        log.exception("Falha ao gerar resposta")
        event_log.add(
            "error",
            "Falha ao processar solicitação",
            f"Comando: {message}\nDetalhes: {exc}",
        )
        await runtime.manager.broadcast({"type": "error", "message": str(exc)})
        await runtime.manager.broadcast({"type": "state", "state": "idle"})
        runtime.track(speech.say_quietly("Desculpe, tive um problema ao processar seu pedido."))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    stop.set()
    if speech.canceled(turn):  # o usuário cancelou enquanto a IA respondia: descarta a resposta
        return {"status": "canceled"}

    cards = await reactive_cards.detect_reactive_cards(message, text)
    session.history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": text}])
    memory.add_conversation(message, text)
    del session.history[:-MAX_HISTORY]

    await runtime.manager.broadcast({"type": "response", "text": text, "cards": cards})
    runtime.track(speech.speak(text))
    return {"status": "ok", "response": text, "cards": cards}
