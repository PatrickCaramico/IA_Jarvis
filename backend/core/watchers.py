"""Laços de serviço: Modo Torcedor (dia de jogo, grito), lembrete de água e gatilhos condicionais."""

import asyncio
import logging
from datetime import datetime

from modules import access, event_log, fan_mode, focus, notifications, prefs, routine, sports_provider, triggers, water
from core import confirm, runtime, session, speech

log = logging.getLogger("jarvis.watchers")


def _say(text: str) -> None:
    """Fala avisos do Modo Torcedor (nada pessoal, então vale também com a central bloqueada)."""
    if not prefs.is_silent_mode():
        runtime.track(speech.speak(text))


def _score_line(match: dict, team: str = "Palmeiras") -> str:
    """'Palmeiras 2 a 0 Remo' (mandante primeiro, como se fala no Brasil)."""
    score = match.get("score") or {}
    h, a = score.get("home", 0), score.get("away", 0)
    if match.get("home_away") == "away":
        return f"{match.get('opponent', 'adversário')} {h} a {a} {team}"
    return f"{team} {h} a {a} {match.get('opponent', 'adversário')}"


def _minute_words(minute: str | None) -> str:
    digits = "".join(ch for ch in str(minute or "") if ch.isdigit() or ch == "+")
    return f", aos {digits.split('+')[0]} minutos" if digits and digits[0].isdigit() else ""


def _matchday_line(match: dict) -> str:
    """Aviso de ativação conforme o momento do jogo (antes, durante ou depois)."""
    status = match.get("status")
    if status == "live":
        if match.get("minute") == "Intervalo":
            return f"Intervalo: {_score_line(match)}."
        return f"Bola rolando: {_score_line(match)}{_minute_words(match.get('minute'))}."
    if status == "finished":
        return f"Hoje teve {_score_line(match)}."
    when = ""
    if match.get("time_known"):
        try:
            when = f" às {datetime.fromisoformat(match['date']):%H:%M}".replace(":00", "h")
        except (KeyError, ValueError):
            when = ""
    where = f", no {match['venue']}" if match.get("venue") and match.get("venue") not in {"A confirmar", "A definir"} else ""
    return f"Hoje tem Palmeiras contra o {match.get('opponent', 'adversário')}{when}{where}."


def _result_word(match: dict) -> str:
    ours, theirs = sports_provider.team_goals(match)
    return "Vitória do Verdão!" if ours > theirs else "Empate." if ours == theirs else "Não foi dessa vez. Bora pro próximo!"


async def _fan_auto_mode(all_prefs: dict, team_id: str, match: dict) -> None:
    """V4.4: liga o Modo Torcedor sozinho no dia do jogo e desliga no dia seguinte.

    Liga uma vez por dia: se você desligar na mão no dia do jogo, ele respeita.
    Só desliga sozinho o que ele mesmo ligou.
    """
    today = sports_provider._now_sp().date().isoformat()
    auto = sports_provider.auto_state()

    if (auto.get("activated_on_match_day") or auto.get("by_auto")) and auto.get("activated_on") != today:
        sports_provider.set_auto_state(by_auto=False, activated_on=today, activated_on_match_day=False)
        if all_prefs.get("fan_mode_enabled"):
            prefs.update({"fan_mode_enabled": False})
            next_match = next((s for s in sports_provider.get_schedule(team_id) if s["seconds_left"] > 0), None)
            if next_match:
                next_game = f"{next_match['opponent']}, {next_match['date_human']}"
            else:
                next_game = "ainda sem data confirmada"
            notice = f"Modo Torcedor desligado. Próximo jogo: {next_game}."
            log.info("Modo Torcedor desligado automaticamente após o dia de jogo.")
            await runtime.manager.broadcast({
                "type": "prefs_updated",
                "fan_mode_enabled": False,
                "notice": notice,
            })
            runtime.notify("fan", "Modo Torcedor desligado", notice)
            _say(notice)
        return

    if match.get("is_match_day") and all_prefs.get("fan_auto_on_match_day"):
        if auto.get("activated_on") == today or all_prefs.get("fan_mode_enabled"):
            return
        prefs.update({"fan_mode_enabled": True})
        sports_provider.set_auto_state(activated_on=today, by_auto=True, activated_on_match_day=True)
        line = _matchday_line(match)
        # V4.4: uma fala só. Se o jogo já começou, o aviso já leva o "Avante Palestra!", então o grito
        # de bola rolando, o intervalo e o fim (se já passaram) ficam marcados como ditos.
        spoken = f"{line} Modo Torcedor ativado."
        if match.get("status") in {"live", "finished"} and match.get("id"):
            sports_provider.mark_shout_fired(match["id"])
            already = ("half",) if match.get("minute") == "Intervalo" else ()
            if match.get("status") == "finished":
                already = ("half", "full")
            sports_provider.take_moments(team_id, mark=already)
            sports_provider.detect_score_change(team_id)  # registra o placar atual (sem comemorar gol antigo)
            spoken += " Avante Palestra!"
        log.info("Modo Torcedor ligado automaticamente: %s", line)
        await runtime.manager.broadcast({
            "type": "prefs_updated",
            "fan_mode_enabled": True,
            "fan_team": team_id,
            "is_match_day": True,
            "fan_auto": True,
            "notice": f"⚽ {line} Modo Torcedor ativado.",
        })
        runtime.notify("fan", "⚽ Dia de jogo", f"{line} Modo Torcedor ativado.")
        _say(spoken)
async def fan_watcher_loop() -> None:
    """Modo Torcedor: atualiza agenda/placar (ESPN + Google Notícias, sem IA), liga sozinho no dia
    de jogo, grita "Avante Palestra!" quando a bola rola e comemora os gols."""
    first = True
    while True:
        try:
            await asyncio.sleep(5 if first else 60)
            first = False
            all_prefs = prefs.get_all()
            team_id = all_prefs.get("fan_team", "palmeiras")
            await asyncio.to_thread(sports_provider.refresh, team_id)
            match_data = await asyncio.to_thread(sports_provider.get_current_or_next_match, team_id)

            # 1) Ativação/desativação automática no dia de jogo
            await _fan_auto_mode(all_prefs, team_id, match_data)
            all_prefs = prefs.get_all()
            if not all_prefs.get("fan_mode_enabled"):
                continue

            team_info = fan_mode.get_team_info(team_id) or {}

            # 2) Grito de torcida quando a bola começa a rolar
            if all_prefs.get("fan_shout_enabled") and await asyncio.to_thread(sports_provider.should_trigger_shout, team_id):
                shout_phrase = team_info.get("shout_phrase", "Avante Palestra!")
                await runtime.manager.broadcast({"type": "fan_shout", "text": shout_phrase, "team": team_id})
                _say(shout_phrase)

            # 3) Gol (placar ao vivo da ESPN), com o autor quando a ESPN já informou
            change = await asyncio.to_thread(sports_provider.detect_score_change, team_id)
            if change:
                m = change["match"]
                if change["kind"] == "goal":
                    scorer = sports_provider.last_goal(m, "ours")
                    who = f" {scorer['player']}{_minute_words(scorer.get('minute'))}." if scorer and scorer.get("player") else ""
                    text = f"{team_info.get('goal_phrase', 'GOL DO PALMEIRAS!')}{who} {_score_line(m)}."
                else:
                    behind = change["theirs"] > change["ours"]
                    tail = "Vamos virar, Verdão!" if behind else "Bora, Verdão!"
                    text = f"Gol do {m.get('opponent', 'adversário')}. {_score_line(m)}. {tail}"
                await runtime.manager.broadcast({
                    "type": "fan_goal",
                    "kind": change["kind"],
                    "text": text,
                    "team": team_id,
                    "match": change["match"],
                })
                runtime.notify("fan", "⚽ GOL DO PALMEIRAS!" if change["kind"] == "goal" else "⚽ Gol do adversário", text)
                if all_prefs.get("fan_shout_enabled"):
                    _say(text)

            # 4) Intervalo e fim de jogo, uma vez cada
            moments, m = await asyncio.to_thread(sports_provider.take_moments, team_id)
            for moment in moments:
                if moment == "half":
                    text = f"Intervalo: {_score_line(m)}."
                else:
                    text = f"Fim de jogo: {_score_line(m)}. {_result_word(m)}"
                await runtime.manager.broadcast({"type": "fan_moment", "kind": moment, "text": text, "match": m, "team": team_id})
                runtime.notify("fan", "⚽ Intervalo" if moment == "half" else "⚽ Fim de jogo", text)
                if all_prefs.get("fan_shout_enabled"):
                    _say(text)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.warning("Erro no fan_watcher_loop: %s", exc)
            await asyncio.sleep(30)


async def water_watcher_loop() -> None:
    """Verifica periodicamente a necessidade de hidratação do operador."""
    while True:
        try:
            await asyncio.sleep(120)
            if await asyncio.to_thread(water.should_remind_water):
                st = await asyncio.to_thread(water.get_status)
                text = f"Hora de um copo d'água, senhor. Hoje foram {st['total_ml']} de {st['goal_ml']} ml."
                # V6.8: no fim do dia, avisa se a ofensiva está em risco
                if st.get("streak_base", 0) > 0 and not st.get("streak_today_done") and datetime.now().hour >= 17:
                    left = st["goal_ml"] - st["total_ml"]
                    text += f" Faltam {left} ml para manter sua ofensiva de {st['streak_base']} dias."
                await runtime.manager.broadcast({"type": "alert", "text": text})
                runtime.notify("water", "💧 Hora da água", text)
                if not prefs.is_silent_mode():
                    runtime.track(speech.speak(text))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.warning("Erro em water_watcher_loop: %s", exc)
            await asyncio.sleep(60)


async def news_watcher_loop() -> None:
    """V6.5: manchetes novas dos temas do briefing viram aviso no celular (sem falar no PC)."""
    from modules import news_alerts

    await asyncio.sleep(120)
    while True:
        try:
            found = await asyncio.to_thread(news_alerts.check_once)
            for theme, item in found:
                title, body = news_alerts.notice_text(theme, item)
                runtime.notify("news", title, body)
            if found:
                log.info("Notícias novas para o celular: %d", len(found))
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("Erro em news_watcher_loop: %s", exc)
        await asyncio.sleep(news_alerts.EVERY_SECONDS)


TRIGGER_LOCKED_TEXT = "Tenho um aviso novo, senhor. Libere a central para ver os detalhes."


async def triggers_watcher_loop() -> None:
    """Gatilhos condicionais (4.2): chuva amanhã, jogo em breve, processador alto, água atrasada."""
    while True:
        try:
            await asyncio.sleep(60)
            p = await asyncio.to_thread(prefs.get_all)
            alerts = await asyncio.to_thread(
                triggers.check_all, p.get("triggers"), bool(p.get("fan_mode_enabled")), p.get("fan_team", "palmeiras")
            )
            await _maybe_suggest_routine(p)
            for alert in alerts:
                text = TRIGGER_LOCKED_TEXT if access.is_restricted() else alert["text"]
                await asyncio.to_thread(event_log.add, "trigger", alert["kind"], alert["text"])
                await runtime.manager.broadcast({"type": "alert", "text": text, "trigger": alert["kind"]})
                runtime.notify("trigger", "Aviso do JARVIS", alert["text"])
                if not prefs.is_silent_mode() and not triggers.is_quiet(datetime.now(triggers.SP_TZ)):
                    runtime.track(speech.say_quietly(text))
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("Erro em triggers_watcher_loop: %s", exc)
            await asyncio.sleep(60)


async def _maybe_suggest_routine(p: dict) -> None:
    """Sugestão pela rotina (4.2): só com a central liberada, o JARVIS livre e nada pendente."""
    if not p.get("routine_suggestions_enabled", True) or access.is_restricted() or session.busy or confirm.pending():
        return
    habit = await asyncio.to_thread(routine.due_suggestion)
    if not habit:
        return
    confirm.offer("routine", habit)
    await runtime.manager.broadcast({"type": "alert", "text": habit["text"], "suggestion": habit["key"]})
    if not prefs.is_silent_mode() and not triggers.is_quiet(datetime.now(triggers.SP_TZ)):
        runtime.track(speech.say_quietly(habit["text"]))


async def notifications_watcher_loop() -> None:
    """Central de notificações (4.2, experimental): só roda com a opção ligada."""
    while True:
        try:
            await asyncio.sleep(20)
            p = await asyncio.to_thread(prefs.get_all)
            if not p.get("notifications_enabled"):
                continue
            new = await notifications.poll()
            if not new or access.is_restricted():
                continue  # bloqueado: nada pessoal na tela nem em voz
            await runtime.manager.broadcast({"type": "notifications", "items": notifications.items()[:5],
                                             "new": len(new)})
            focus_on = focus.session.active and focus.session.phase == "work"  # "não perturbe" do JARVIS
            if focus_on or prefs.is_silent_mode() or triggers.is_quiet(datetime.now(triggers.SP_TZ)):
                continue
            text = notifications.spoken_summary(new, bool(p.get("notifications_read_content")))
            if text and not session.busy:
                runtime.track(speech.say_quietly(text))
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("Erro em notifications_watcher_loop: %s", exc)
            await asyncio.sleep(60)
