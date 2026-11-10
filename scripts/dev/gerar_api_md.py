"""Gera docs/API.md a partir das rotas reais do backend (refatoração 4.2).

Uso (na raiz do projeto):  backend\\venv\\Scripts\\python.exe scripts\\dev\\gerar_api_md.py
Lê backend/routes/*.py sem iniciar o servidor e cruza com a política de acesso (modules/access.py).
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

AREAS = {
    "system": "Sistema, conversa e WebSocket",
    "access": "Acesso: rosto, PIN, visitante e bloqueio",
    "profile": "Perfil, \"sobre mim\" e preferências",
    "water": "Hidratação",
    "productivity": "Atalhos, tarefas, lembretes, foco, briefing e memória",
    "info": "Informações: notícias, sistema, volume, clima, finanças",
    "search": "Busca profunda",
    "fan": "Modo Torcedor",
    "integrations": "Integrações (Google Agenda e Spotify)",
    "health": "Saúde (biometria e relógios Bluetooth)",
    "mobile": "JARVIS no celular",
    "profiles": "Perfis por pessoa",
}


# Descrição para rotas ainda sem docstring no código.
DESCRICOES = {
    "health": "Estado dos serviços (backend, IA, câmera, perfil, timers).",
    "list_timers": "Timers ativos.",
    "websocket_endpoint": "Canal em tempo real com a interface (eventos abaixo).",
    "get_logs": "Últimos eventos registrados.",
    "get_access": "Estado de acesso atual (bloqueada, liberada ou visitante).",
    "pin_status": "Se há PIN cadastrado e se está temporariamente travado.",
    "pin_verify": "Libera a central com o PIN.",
    "pin_set": "Cadastra ou troca o PIN.",
    "pin_delete": "Remove o PIN.",
    "get_lock_log": "Registro de tentativas de acesso.",
    "clear_lock_log": "Apaga o registro de tentativas e as fotos de intrusos.",
    "get_about": "Lê o texto \"sobre mim\".",
    "save_about": "Salva o texto \"sobre mim\".",
    "get_profile": "Nome e se há foto de perfil.",
    "get_profile_photo": "Foto de perfil.",
    "save_profile": "Cadastra ou troca nome e foto de perfil.",
    "list_tasks": "Lista as tarefas.",
    "create_task": "Cria uma tarefa.",
    "mark_task_complete": "Conclui uma tarefa.",
    "remove_task": "Apaga uma tarefa.",
    "list_reminders": "Lista os lembretes.",
    "create_reminder": "Cria um lembrete.",
    "remove_reminder": "Apaga um lembrete.",
    "get_focus_status": "Estado do modo foco (Pomodoro).",
    "start_focus_session": "Inicia o modo foco.",
    "stop_focus_session": "Encerra o modo foco.",
    "get_briefing": "Resumo do dia em texto corrido (o \"bom dia\" na central usa o briefing em etapas).",
    "get_memory": "Memórias salvas.",
    "save_memory": "Salva uma memória.",
    "get_system_status": "CPU, memória, disco e volume do computador.",
    "set_system_volume": "Muda o volume do Windows.",
    "google_calendar_status": "Se o Google Agenda está configurado e conectado.",
    "google_calendar_authorize": "Inicia o login no Google Agenda.",
    "google_calendar_callback": "Retorno do login do Google (OAuth).",
    "google_calendar_disconnect": "Desconecta o Google Agenda.",
    "google_calendar_events": "Próximos eventos da agenda.",
    "spotify_status": "Se o Spotify está configurado e conectado.",
    "spotify_now_playing": "Música tocando agora.",
    "spotify_play_search": "Procura e toca uma música ou playlist.",
    "spotify_authorize": "Inicia o login no Spotify.",
    "spotify_callback": "Retorno do login do Spotify (OAuth).",
    "spotify_disconnect": "Desconecta o Spotify.",
}


def access_label(method: str, path: str) -> str:
    from modules import access  # noqa: PLC0415 - só política, sem estado

    if method == "WS":
        return "token na rede"
    probe = path.replace("{", "").replace("}", "")
    if access.is_allowed(method, probe, access.LOCKED):
        return "sempre"
    if access.is_allowed(method, probe, access.GUEST):
        return "visitante"
    return "liberada"


def routes_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
                continue
            if not (isinstance(deco.func.value, ast.Name) and deco.func.value.id == "router"):
                continue
            method = deco.func.attr.upper()
            method = "WS" if method == "WEBSOCKET" else method
            route = deco.args[0].value
            doc = (ast.get_docstring(node) or "").strip().split("\n")[0]
            yield method, route, doc, node.name


def main() -> None:
    lines = [
        "# API do JARVIS",
        "",
        "Referência gerada a partir do código (`scripts/dev/gerar_api_md.py`). Com o JARVIS ligado, a",
        "documentação interativa do FastAPI fica em `http://127.0.0.1:8000/docs`.",
        "",
        "**Acesso:** `sempre` = funciona até com a central bloqueada; `visitante` = também no modo visitante;",
        "`liberada` = só depois do rosto ou do PIN (o servidor responde 403 `{code: \"locked\"}`).",
        "Fora deste computador, toda chamada precisa do cabeçalho `X-Jarvis-Token` (ou `?token=`) e do modo rede.",
        "",
    ]
    total = 0
    for key, title in AREAS.items():
        file = BACKEND / "routes" / f"{key}.py"
        rows = list(routes_of(file))
        if not rows:
            continue
        lines += [f"## {title}", "", f"Arquivo: `backend/routes/{key}.py`", "",
                  "| Método | Rota | Acesso | O que faz |", "| --- | --- | --- | --- |"]
        for method, route, doc, name in rows:
            desc = doc or DESCRICOES.get(name, name.replace("_", " "))
            lines.append(f"| {method} | `{route}` | {access_label(method, route)} | {desc} |")
            total += 1
        lines.append("")
    lines += [
        "## Eventos do WebSocket (`/ws`)",
        "",
        "| Evento | Quando |",
        "| --- | --- |",
        "| `state` | idle, processing ou speaking |",
        "| `step` | etapa do processamento (câmera, notícias, IA, voz) |",
        "| `response` / `error` / `alert` | resposta, erro ou aviso de timer/lembrete |",
        "| `access_state` | central bloqueada, liberada ou em modo visitante |",
        "| `face_scan_start` / `face_frame` / `face_scan_end` | escaneamento facial ao vivo (só para este computador) |",
        "| `sentinel_reply` | resposta do Modo Sentinela |",
        "| `water_updated` | mudança no registro de água |",
        "| `prefs_updated` / `fan_shout` | Modo Torcedor ligado sozinho / grito da torcida |",
        "| `notice` / `reset` | aviso curto / limpar a resposta anterior |",
        "| `briefing_start` | \"bom dia\": abas do briefing, saudação e abertura (\"Sem desvios relevantes\") |",
        "| `briefing_step` | um assunto do briefing: aba, texto de progresso e o card falado agora |",
        "| `briefing_end` | fim do briefing: todos os cards, prontidão e recomendação do dia |",
        "",
        f"Total: {total} rotas.",
        "",
    ]
    out = ROOT / "docs" / "API.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"docs/API.md gerado com {total} rotas.")


if __name__ == "__main__":
    main()
