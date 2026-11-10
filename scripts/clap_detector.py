"""Detecção de PALMA DUPLA a partir da energia do áudio (lógica pura, sem microfone).

Espelho exato de frontend/src/utils/clapDetector.js. As duas versões são testadas com as
mesmas sequências de tests/fixtures/clap_sequences.json para concordarem.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

DEFAULTS = {
    "min_gap_ms": 120,
    "max_gap_ms": 800,
    "pre_silence_ms": 300,
    "post_silence_min_ms": 400,
    "post_silence_max_ms": 900,
    "refractory_ms": 60,
    "max_peak_ms": 120,
    "cooldown_ms": 3000,
    "floor_tau_ms": 600,
}


def sensitivity_params(sensitivity: float = 5) -> tuple[float, float]:
    """Fator sobre o piso e mínimo absoluto (RMS) para a sensibilidade de 1 a 10."""
    try:
        s = int(round(float(sensitivity)))
    except (TypeError, ValueError):
        s = 5
    s = min(10, max(1, s))
    return 12 - (s - 1), 0.12 - ((s - 1) * 0.1) / 9


def post_silence_for(gap_ms: float, opts: dict = DEFAULTS) -> float:
    return min(opts["post_silence_max_ms"], max(opts["post_silence_min_ms"], gap_ms * 1.25))


@dataclass
class ClapDetector:
    sensitivity: float = 5
    options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.opts = {**DEFAULTS, **self.options}
        self.factor, self.min_abs = sensitivity_params(self.sensitivity)
        self.reset()

    def set_sensitivity(self, sensitivity: float) -> None:
        self.factor, self.min_abs = sensitivity_params(sensitivity)

    def reset(self) -> None:
        self.floor: Optional[float] = None
        self.last_t: Optional[float] = None
        self.last_loud_end = -math.inf
        self.in_peak = False
        self.peak_start = 0.0
        self.peak_too_long = False
        self.refractory_until = -math.inf
        self.cooldown_until = -math.inf
        self.claps: list[float] = []

    def _onset(self, t: float) -> None:
        o = self.opts
        self.in_peak = True
        self.peak_start = t
        self.peak_too_long = False
        self.refractory_until = t + o["refractory_ms"]
        if t < self.cooldown_until:
            return
        quiet_before = t - self.last_loud_end
        if not self.claps:
            if quiet_before >= o["pre_silence_ms"]:
                self.claps = [t]
        elif len(self.claps) == 1:
            gap = t - self.claps[0]
            if gap < o["min_gap_ms"]:
                self.claps = []
            elif gap <= o["max_gap_ms"]:
                self.claps.append(t)
            else:
                self.claps = [t] if quiet_before >= o["pre_silence_ms"] else []
        else:
            self.claps = []  # terceira palma logo em seguida

    def process(self, energy: float, t: float) -> Optional[str]:
        o = self.opts
        try:
            e = float(energy)
            if not math.isfinite(e):
                e = 0.0
        except (TypeError, ValueError):
            e = 0.0
        e = max(0.0, e)
        dt = 10.0 if self.last_t is None else max(1.0, t - self.last_t)
        self.last_t = t
        alpha = 1 - math.exp(-dt / o["floor_tau_ms"])
        if self.floor is None:
            self.floor = e
        threshold = max(self.floor * self.factor, self.min_abs)
        loud = e > threshold

        if self.in_peak:
            if loud:
                if t - self.peak_start > o["max_peak_ms"]:
                    self.peak_too_long = True
                    self.claps = []
                    self.floor += (e - self.floor) * alpha
            else:
                self.in_peak = False
                self.last_loud_end = t
                if self.peak_too_long:
                    self.claps = []
                self.peak_too_long = False
                self.floor += (e - self.floor) * alpha
        elif loud and t >= self.refractory_until:
            self._onset(t)
        elif not loud:
            self.floor += (e - self.floor) * alpha

        if len(self.claps) == 2 and not self.in_peak:
            gap = self.claps[1] - self.claps[0]
            if t - self.claps[1] >= post_silence_for(gap, o):
                self.claps = []
                self.cooldown_until = t + o["cooldown_ms"]
                return "double"
        return None


# ------------------------------------------------------------------ sequências de teste
def _park_miller(seed: int):
    state = max(1, int(seed) % 2147483647)

    def rand() -> float:
        nonlocal state
        state = (state * 48271) % 2147483647
        return state / 2147483647

    return rand


def expand_sequence(seq: dict, frame_ms: int = 10) -> list[tuple[float, float]]:
    rand = _park_miller(seq.get("seed", 1))
    frames = []
    events = seq.get("events", [])
    for t in range(0, int(seq["duration_ms"]), frame_ms):
        base = seq.get("noise", 0.005)
        for ev in events:
            if ev["type"] == "noise_level" and t >= ev["t"]:
                base = ev["level"]
        e = base * (0.6 + 0.8 * rand())
        for ev in events:
            dt_ev = t - ev["t"]
            if ev["type"] == "clap" and 0 <= dt_ev < 30:
                e = max(e, ev["level"] * (1 - (dt_ev / 30) * 0.7))
            elif ev["type"] == "sustained" and 0 <= dt_ev < ev["dur"]:
                e = max(e, ev["level"])
            elif ev["type"] == "speech" and 0 <= dt_ev < ev["dur"]:
                if dt_ev % 250 < 180:
                    e = max(e, ev["level"])
        frames.append((e, float(t)))
    return frames


def count_doubles(seq: dict, frame_ms: int = 10) -> int:
    det = ClapDetector(seq.get("sensitivity", 5), {"cooldown_ms": seq.get("cooldown_ms", 3000)})
    return sum(1 for e, t in expand_sequence(seq, frame_ms) if det.process(e, t) == "double")
