"""Segurança e otimização (V9.3): o vigia da câmera, o alerta de pendrive, a otimização do dia e o relatório.

Tudo local: nenhuma imagem sai do PC (o rosto é comparado pelo modules/face.py, como no desbloqueio).

Vigia da câmera (desligado por padrão; "liga o vigia da câmera" ou Configurações > Bloqueio):
  - central BLOQUEADA: olha a cada ~20 s. Pessoa que não é de casa em duas olhadas seguidas = aviso no celular e na
    tela, a foto vai para o relatório e o JARVIS diz que não a reconhece;
  - central LIBERADA: olha a cada ~60 s. Outra pessoa sozinha na frente do PC = bloqueia a central (com foto);
    o senhor fora da frente do PC por X minutos = bloqueia sozinho (e o Windows também, se escolhido).
Pendrive: avisa quando um pendrive/HD externo é ligado (e registra).
Otimização: 1x por dia, com o PC parado há 10 min, faz a varredura (temporários, lixeira, programas que abrem com o
Windows); se valer a pena, deixa a sugestão no relatório — nada é apagado sem o senhor mandar.
Relatório: "relatório de segurança", "alguém tentou entrar?". Ao abrir a central, as novidades aparecem sozinhas.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Optional

from config import settings
from core import safe_io
from core.skills import Permission, SkillContext, SkillResult, service, skill

log = logging.getLogger("jarvis.skills.seguranca")

_PATH = settings.DATA_DIR / "seguranca.json"
MAX_EVENTS = 200
ALERT_KINDS = {"intruso", "estranho", "tentativa", "usb", "otimizacao"}
KIND_LABEL = {"intruso": "Pessoa não reconhecida", "estranho": "Bloqueio: outra pessoa", "tentativa": "Tentativa de entrar",
              "usb": "Pendrive", "otimizacao": "Otimização", "ausente": "Bloqueio: o senhor saiu"}
LOCKED_EVERY_S = 20
UNLOCKED_EVERY_S = 60
EVENT_COOLDOWN_S = 5 * 60
PRESENCE_GAP_S = 150  # sem o senhor por mais que isso = saiu da frente do PC


# ------------------------------------------------------------------ registro
def _load() -> dict:
    try:
        data = safe_io.read_json(_PATH) if _PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("events", [])
    data.setdefault("seen_at", "")
    return data


def _save(data: dict) -> None:
    safe_io.write_json(_PATH, data)


def add_event(kind: str, text: str, photo: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    data = _load()
    ev = {"id": uuid.uuid4().hex[:12], "at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": text}
    if photo:
        ev["photo"] = photo
    if extra:
        ev.update(extra)
    data["events"] = (data["events"] + [ev])[-MAX_EVENTS:]
    _save(data)
    return ev


def unseen(data: Optional[dict] = None) -> list[dict]:
    data = data or _load()
    return [e for e in data["events"] if e["kind"] in ALERT_KINDS and e["at"] > (data.get("seen_at") or "")]


def mark_seen() -> None:
    data = _load()
    data["seen_at"] = datetime.now().isoformat(timespec="seconds")
    _save(data)


def summary_speech(events: list[dict]) -> str:
    """Frase curta do que aconteceu (do mais grave ao mais leve)."""
    if not events:
        return "Nenhuma novidade de segurança, senhor. Ninguém tentou entrar."
    count = {k: sum(1 for e in events if e["kind"] == k) for k in ("intruso", "estranho", "tentativa", "usb", "otimizacao")}
    parts = []
    people = count["intruso"] + count["estranho"] + count["tentativa"]
    if people:
        last = max((e for e in events if e["kind"] in {"intruso", "estranho", "tentativa"}), key=lambda e: e["at"])
        parts.append(f"{people} {'vez' if people == 1 else 'vezes'} alguém que não reconheço esteve na frente do PC; "
                     f"a última às {last['at'][11:16]}")
    if count["usb"]:
        parts.append(f"{count['usb']} {'pendrive ligado' if count['usb'] == 1 else 'pendrives ligados'}")
    if count["otimizacao"]:
        parts.append("uma sugestão de otimização")
    from skills.workspace.layouts import spoken_list

    return f"Senhor, desde a última vez: {spoken_list(parts)}. As fotos e os detalhes estão no relatório."


# ------------------------------------------------------------------ vigia da câmera (parte pura)
class CameraGuard:
    """Decide o que fazer a cada olhada. Devolve ações: "intruso" | "estranho" | "ausente"."""

    def __init__(self) -> None:
        self.unknown_streak = 0
        self.last_owner: Optional[float] = None
        self.was_locked: Optional[bool] = None
        self.last_event: dict[str, float] = {}
        self.present_since: Optional[float] = None
        self.absences = 0
        self.day = ""

    def _due(self, kind: str, now: float, cooldown: float) -> bool:
        if now - self.last_event.get(kind, -1e12) < cooldown:
            return False
        self.last_event[kind] = now
        return True

    def step(self, now: float, locked: bool, look: dict, away_minutes: int = 5, auto_lock: bool = True) -> list[str]:
        if self.was_locked is not False and not locked:  # acabou de liberar: o dono está aí
            self.last_owner = now
            self.unknown_streak = 0
        self.was_locked = locked
        known, unknown = int(look.get("known") or 0), int(look.get("unknown") or 0)
        today = time.strftime("%Y-%m-%d", time.localtime(now))
        if today != self.day:  # as saídas contam por dia
            self.day, self.absences = today, 0
        if known:
            if self.present_since is None:
                self.present_since = now
            self.last_owner = now
        elif self.present_since is not None and self.last_owner is not None and now - self.last_owner > PRESENCE_GAP_S:
            self.present_since = None
            self.absences += 1
        self.unknown_streak = self.unknown_streak + 1 if unknown and not known else 0
        actions = []
        if locked:
            if self.unknown_streak >= 2 and self._due("intruso", now, EVENT_COOLDOWN_S):
                actions.append("intruso")
        elif self.unknown_streak >= 2 and auto_lock and self._due("estranho", now, EVENT_COOLDOWN_S):
            actions.append("estranho")
        elif (auto_lock and not known and not unknown and self.last_owner is not None
              and now - self.last_owner >= away_minutes * 60 and self._due("ausente", now, away_minutes * 60)):
            actions.append("ausente")
        return actions

    def presence(self, now: float) -> dict:
        return {"present": self.present_since is not None, "minutes": int((now - self.present_since) // 60) if self.present_since else 0,
                "absences": self.absences}


_guard = CameraGuard()


def _prefs() -> dict:
    from modules import prefs

    return prefs.get_all()


def _lock_windows() -> None:
    import subprocess

    if os.name == "nt":
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])  # noqa: S603 - sem shell, argumentos fixos


async def _on_action(action: str, look: dict) -> None:
    from core import runtime, speech
    from modules import access, lock_log

    p = _prefs()
    photo = None
    if action in {"intruso", "estranho"} and look.get("jpeg"):
        saved = await asyncio.to_thread(lock_log.save_intruder, look["jpeg"])
        photo = saved.name if saved else None
    hhmm = datetime.now().strftime("%H:%M")
    if action == "intruso":
        text = f"Uma pessoa que não reconheço apareceu na frente do PC às {hhmm}, com a central bloqueada."
        add_event("intruso", text, photo)
        runtime.notify("security", "🚨 Pessoa não reconhecida", text)
        await runtime.manager.broadcast({"type": "alert", "text": "Pessoa não reconhecida na frente do PC. O dono foi avisado."})
        runtime.track(speech.say_quietly("Não reconheço quem está aí. O acesso continua bloqueado e o dono foi avisado."))
    elif action == "estranho":
        access.lock("camera")
        lock_log.add("camera", "lock")
        text = f"Às {hhmm}, outra pessoa estava sozinha na frente do PC com a central aberta: bloqueei a central."
        add_event("estranho", text, photo)
        runtime.notify("security", "🔒 Central bloqueada", text)
        await speech.broadcast_access()
        if p.get("camera_guard_lock_windows"):
            await asyncio.to_thread(_lock_windows)
        runtime.track(speech.say_quietly("Não reconheço quem está aí. Bloqueei a central por segurança."))
    elif action == "ausente":
        access.lock("ausente")
        lock_log.add("away", "lock")
        add_event("ausente", f"O senhor saiu da frente do PC: bloqueei a central às {hhmm}.")
        await speech.broadcast_access()
        if p.get("camera_guard_lock_windows"):
            await asyncio.to_thread(_lock_windows)
    log.info("Vigia da câmera: %s", action)


def _refs():
    from modules import profiles

    return profiles.face_refs() if profiles.count() > 1 else None


@service("vigia_camera")
async def camera_loop() -> None:
    from core import session
    from modules import access, face

    errors = 0
    while True:
        p = _prefs()
        if not p.get("camera_guard_enabled") or not face.has_profile():
            _guard.__init__()
            await asyncio.sleep(10)
            continue
        locked = access.is_restricted()
        await asyncio.sleep(LOCKED_EVERY_S if locked else UNLOCKED_EVERY_S)
        if session.busy or session.auth_lock.locked():
            continue  # a câmera está sendo usada (desbloqueio, visão da IA): olha na próxima
        try:
            async with session.auth_lock:
                look = await asyncio.to_thread(face.look_once, _refs())
            errors = 0
        except Exception:  # noqa: BLE001 - sem câmera ou ocupada por outro programa: tenta de novo mais tarde
            errors += 1
            log.warning("Vigia da câmera: não consegui olhar (%d)", errors, exc_info=errors == 1)
            await asyncio.sleep(min(300, 30 * errors))
            continue
        locked = access.is_restricted()
        for action in _guard.step(time.time(), locked, look, int(p.get("camera_guard_away_minutes") or 5),
                                  bool(p.get("camera_guard_auto_lock", True))):
            try:
                await _on_action(action, look)
            except Exception:  # noqa: BLE001
                log.exception("Vigia da câmera: a ação %s falhou", action)


# ------------------------------------------------------------------ pendrive / HD externo
def removable_drives() -> dict[str, str]:
    """{ponto de montagem: descrição} dos discos removíveis ligados agora."""
    import psutil

    out = {}
    for part in psutil.disk_partitions(all=False):
        if "removable" not in (part.opts or "").lower():
            continue
        try:
            size = psutil.disk_usage(part.mountpoint).total / 1024 ** 3
            out[part.mountpoint] = f"{part.mountpoint} ({size:.0f} GB)".replace(".", ",")
        except OSError:
            out[part.mountpoint] = part.mountpoint
    return out


def new_drives(before: dict, now: dict) -> list[str]:
    return [now[m] for m in now if m not in before]


@service("vigia_usb")
async def usb_loop() -> None:
    from core import runtime

    known: Optional[dict] = None
    while True:
        await asyncio.sleep(5)
        if not _prefs().get("usb_alert_enabled", True):
            known = None
            continue
        try:
            current = await asyncio.to_thread(removable_drives)
        except Exception:  # noqa: BLE001
            log.debug("Vigia de pendrive: leitura falhou", exc_info=True)
            continue
        if known is not None:
            for desc in new_drives(known, current):
                text = f"Pendrive ou HD externo ligado no PC às {datetime.now().strftime('%H:%M')}: {desc}."
                add_event("usb", text)
                runtime.notify("security", "🔌 Pendrive ligado", text)
                await runtime.manager.broadcast({"type": "alert", "text": text})
        known = current


# ------------------------------------------------------------------ otimização do dia
OPT_IDLE_S = 10 * 60


def worth_optimizing(scan: dict) -> list[str]:
    """O que vale sugerir (frases curtas); vazio = nada a fazer."""
    out = []
    if (scan.get("temp_bytes") or 0) >= 300 * 1024 ** 2:
        out.append(f"{scan['temp_bytes'] / 1024 ** 3:.1f} GB de arquivos temporários".replace(".", ","))
    if (scan.get("recycle_bytes") or 0) >= 500 * 1024 ** 2:
        out.append(f"{scan['recycle_bytes'] / 1024 ** 3:.1f} GB na lixeira".replace(".", ","))
    if (scan.get("startup") or 0) >= 8:
        out.append(f"{scan['startup']} programas abrindo junto com o Windows")
    if (scan.get("disk_percent") or 0) >= 90:
        out.append(f"o disco {scan['disk_percent']}% cheio")
    return out


@service("otimizacao_diaria")
async def optimize_loop() -> None:
    from core import runtime
    from modules import pc_scan

    while True:
        await asyncio.sleep(10 * 60)
        if not _prefs().get("auto_optimize_enabled", True):
            continue
        now = datetime.now()
        data = _load()
        if data.get("optimized_day") == now.date().isoformat() or not 9 <= now.hour < 23:
            continue
        try:
            from skills import tempo_de_tela

            idle = await asyncio.to_thread(tempo_de_tela.idle_seconds)
        except Exception:  # noqa: BLE001
            idle = 0
        if idle < OPT_IDLE_S:
            continue
        try:
            scan = await asyncio.to_thread(pc_scan.scan)
        except Exception:  # noqa: BLE001
            log.exception("Otimização do dia: a varredura falhou")
            continue
        data = _load()
        data["optimized_day"] = now.date().isoformat()
        _save(data)
        items = worth_optimizing(scan)
        if not items:
            continue
        from skills.workspace.layouts import spoken_list

        text = f"Na otimização do dia encontrei {spoken_list(items)}. Abra o relatório de segurança para limpar com um toque."
        add_event("otimizacao", text, extra={"scan": scan})
        runtime.notify("system", "🧹 Otimização sugerida", text)


# ------------------------------------------------------------------ skills
_REPORT_RE = re.compile(r"\b(?:relatorio de seguranca|alguem (?:tentou|quis) (?:entrar|mexer|usar)|quem (?:tentou|quis) "
                        r"(?:entrar|mexer|usar)|alguem mexeu no (?:meu )?(?:pc|computador)|teve (?:algum )?intruso)\b")


@skill(
    name="relatorio_de_seguranca",
    title="ver o relatório de segurança",
    description=("Relatório de segurança: quem tentou entrar ou apareceu na câmera sem ser reconhecido (com foto), "
                 "pendrives ligados, bloqueios automáticos e a sugestão de otimização do dia."),
    permission=Permission.READ,
    timeout=8,
    triggers=[_REPORT_RE.pattern],
    params={"type": "object", "properties": {}},
    examples=["relatório de segurança", "alguém tentou entrar?"],
)
async def relatorio_de_seguranca(ctx: SkillContext) -> SkillResult:
    data = await asyncio.to_thread(_load)
    news = unseen(data)
    recent = data["events"][-8:][::-1]
    rows = [{"label": e["at"][11:16] + " · " + KIND_LABEL.get(e["kind"], e["kind"]), "value": e["text"]} for e in recent]
    await ctx.broadcast({"type": "open_panel", "panel": "security"})
    return SkillResult(speech=summary_speech(news) if news else summary_speech([]),
                       cards=[{"type": "skill", "data": {"tag": "SEGURANÇA", "source": f"{len(news)} novidades", "rows": rows}}])


_CAM_RE = re.compile(r"\b(?P<verb>liga|ligue|ativa|ative|desliga|desligue|desativa|desative)\s+(?:o\s+|a\s+)?"
                     r"(?:vigia|vigilancia|seguranca)\s+(?:da|pela|com a)\s+camera\b")


def _parse_cam(norm: str, _original: str) -> Optional[dict]:
    m = _CAM_RE.search(norm)
    return {"ativo": not m.group("verb").startswith("des")} if m else None


@skill(
    name="vigia_da_camera",
    title="ligar o vigia da câmera",
    description=("Liga ou desliga o vigia da câmera: com a central bloqueada avisa sobre pessoas não reconhecidas (com "
                 "foto); liberada, bloqueia se o usuário sair ou se outra pessoa estiver sozinha no PC. Tudo local."),
    permission=Permission.ACTION,
    allow_remote=False,
    timeout=5,
    parse=_parse_cam,
    params={"type": "object", "required": ["ativo"], "properties": {"ativo": {"type": "boolean"}}},
    examples=["liga o vigia da câmera", "desliga o vigia da câmera"],
)
def vigia_da_camera(ctx: SkillContext, ativo: bool) -> SkillResult:
    from modules import face, prefs

    if ativo and not face.has_profile():
        return SkillResult(ok=False, speech="Preciso da foto do seu rosto cadastrada antes, senhor. Ela fica em Configurações, Bloqueio.")
    prefs.update(camera_guard_enabled=bool(ativo))
    if not ativo:
        return SkillResult(speech="Vigia da câmera desligado, senhor.")
    away = prefs.get_all().get("camera_guard_away_minutes", 5)
    return SkillResult(speech=f"Vigia da câmera ligado, senhor. Tudo fica no PC; se o senhor sair por {away} minutos ou "
                              "outra pessoa aparecer sozinha, eu bloqueio a central.")


# "quanto tempo eu FIQUEI no PC hoje" é do tempo de tela (skills/tempo_de_tela.py); aqui é o "agora", pela câmera
_PRESENCE_RE = re.compile(r"\bha quanto tempo\s+(?:eu\s+)?(?:estou|to|tou)\s+(?:na frente do|no)\s+"
                          r"(?:pc|computador)\b|\bo que eu (?:estou|to|tou) fazendo\b")


@skill(
    name="presenca_no_pc",
    title="ver há quanto tempo o senhor está no PC",
    description="Diz há quanto tempo o usuário está na frente do PC e quantas vezes saiu (vigia da câmera, local).",
    permission=Permission.READ,
    timeout=5,
    triggers=[_PRESENCE_RE.pattern],
    params={"type": "object", "properties": {}},
    examples=["há quanto tempo eu estou no PC?"],
)
def presenca_no_pc(ctx: SkillContext) -> SkillResult:
    if not _prefs().get("camera_guard_enabled"):
        return SkillResult(speech="Para eu acompanhar, ligue o vigia da câmera, senhor: diga 'liga o vigia da câmera'. "
                                  "Tudo fica no PC.")
    st = _guard.presence(time.time())
    if not st["present"]:
        return SkillResult(speech="Não vejo o senhor na frente do PC agora.")
    h, m = divmod(st["minutes"], 60)
    span = (f"{h} hora{'s' if h != 1 else ''} e {m} minutos" if h else f"{m} minutos") if st["minutes"] else "menos de um minuto"
    out = f" e saiu {st['absences']} {'vez' if st['absences'] == 1 else 'vezes'} hoje" if st["absences"] else ""
    tip = " Que tal uma pausa para esticar as pernas?" if st["minutes"] >= 90 else ""
    return SkillResult(speech=f"O senhor está na frente do PC há {span}{out}.{tip}")
