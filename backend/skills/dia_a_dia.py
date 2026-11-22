"""Skills do dia a dia (V8.11): conversor de unidades local e gerador de senha forte.

Conversor (sem IA, resposta na hora, vale com a central bloqueada):
- "quanto é 5 milhas em km", "converte 350 fahrenheit para celsius", "2 xícaras em ml",
  "quantos gramas tem 3 libras", "10 polegadas em centímetros", "100 km/h em mph", "1,5 gb em mb"
  (número falado por extenso também: "cinco milhas em quilômetros")
Senha:
- "gera uma senha forte", "cria uma senha de 16 caracteres": vai direto para a área de transferência do PC.
  A senha nunca é falada nem mostrada na tela (só "copiei, é só colar").
"""
from __future__ import annotations

import re
import secrets
import string
from typing import Optional

from core.skills import Permission, SkillContext, SkillResult, skill

# ------------------------------------------------------------------ unidades
# nome falado (sem acento) -> (grandeza, fator para a unidade base, singular, plural)
_UNITS: dict[str, tuple[str, float, str, str]] = {}


def _add(kind: str, factor: float, sing: str, plural: str, *aliases: str) -> None:
    for alias in aliases:
        _UNITS[alias] = (kind, factor, sing, plural)


_add("comprimento", 1000, "quilômetro", "quilômetros", "km", "quilometro", "quilometros", "kilometro", "kilometros")
_add("comprimento", 1, "metro", "metros", "m", "metro", "metros")
_add("comprimento", 0.01, "centímetro", "centímetros", "cm", "centimetro", "centimetros")
_add("comprimento", 0.001, "milímetro", "milímetros", "mm", "milimetro", "milimetros")
_add("comprimento", 1609.344, "milha", "milhas", "mi", "milha", "milhas")
_add("comprimento", 0.3048, "pé", "pés", "pe", "pes", "ft")
_add("comprimento", 0.0254, "polegada", "polegadas", "polegada", "polegadas", "pol")
_add("comprimento", 0.9144, "jarda", "jardas", "jarda", "jardas")
_add("massa", 1000, "quilo", "quilos", "kg", "quilo", "quilos", "quilograma", "quilogramas", "kilo", "kilos")
_add("massa", 1, "grama", "gramas", "g", "grama", "gramas")
_add("massa", 0.001, "miligrama", "miligramas", "mg", "miligrama", "miligramas")
_add("massa", 1_000_000, "tonelada", "toneladas", "tonelada", "toneladas")
_add("massa", 453.59237, "libra", "libras", "lb", "lbs", "libra", "libras")
_add("massa", 28.349523125, "onça", "onças", "oz", "onca", "oncas")
_add("volume", 1000, "litro", "litros", "l", "litro", "litros")
_add("volume", 1, "mililitro", "mililitros", "ml", "mililitro", "mililitros")
_add("volume", 240, "xícara", "xícaras", "xicara", "xicaras")
_add("volume", 15, "colher de sopa", "colheres de sopa", "colher de sopa", "colheres de sopa")
_add("volume", 5, "colher de chá", "colheres de chá", "colher de cha", "colheres de cha")
_add("volume", 3785.411784, "galão", "galões", "galao", "galoes")
_add("velocidade", 1 / 3.6, "quilômetro por hora", "quilômetros por hora", "km/h", "kmh", "km por hora",
     "quilometro por hora", "quilometros por hora")
_add("velocidade", 0.44704, "milha por hora", "milhas por hora", "mph", "milha por hora", "milhas por hora")
_add("velocidade", 1, "metro por segundo", "metros por segundo", "m/s", "metro por segundo", "metros por segundo")
_add("dados", 1024 ** 1, "kilobyte", "kilobytes", "kb", "kilobyte", "kilobytes")
_add("dados", 1024 ** 2, "megabyte", "megabytes", "mb", "mega", "megas", "megabyte", "megabytes")
_add("dados", 1024 ** 3, "gigabyte", "gigabytes", "gb", "giga", "gigas", "gigabyte", "gigabytes")
_add("dados", 1024 ** 4, "terabyte", "terabytes", "tb", "tera", "teras", "terabyte", "terabytes")
_TEMPS = {"celsius": "c", "graus celsius": "c", "graus": "c", "c": "c", "fahrenheit": "f", "graus fahrenheit": "f",
          "f": "f", "kelvin": "k", "k": "k"}
_TEMP_NAMES = {"c": ("grau Celsius", "graus Celsius"), "f": ("grau Fahrenheit", "graus Fahrenheit"), "k": ("kelvin", "kelvins")}

_ALL = sorted(set(_UNITS) | set(_TEMPS), key=len, reverse=True)
_U = "|".join(re.escape(u) for u in _ALL)
_NUM = r"\d+(?:[.,]\d+)*"
_CONV_A = re.compile(rf"(?:^|\b)(?:quanto (?:e|sao|da|seria)\s+|converte\s+|converter\s+|transforma\s+|passa\s+)?"
                     rf"(?P<valor>{_NUM})\s*(?P<de>{_U})\s+(?:em|para|pra|to)\s+(?:quantos?\s+|quantas?\s+)?(?P<para>{_U})\b")
_CONV_B = re.compile(rf"\bquant[oa]s?\s+(?P<para>{_U})\s+(?:tem|ha|sao|cabem|da|dao|equivalem a|e)\s+(?:em\s+)?"
                     rf"(?P<valor>{_NUM})\s*(?P<de>{_U})\b")


def _to_float(text: str) -> float:
    """Número em português: vírgula = decimal ("1,5"); ponto com 3 dígitos = milhar ("1.000"); senão decimal ("2.5")."""
    if "," in text:
        return float(text.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        return float(text.replace(".", ""))
    return float(text)


def clean_phrase(original: str) -> str:
    """Minúsculas e sem acento, MAS com vírgula/ponto decimal e "km/h" (a normalização padrão apaga os dois)."""
    import unicodedata

    from modules import tools

    t = unicodedata.normalize("NFKD", (original or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[°º]", " ", t)
    t = re.sub(r"[^a-z0-9,./ ]+", " ", t)
    t = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", t)  # pontuação que não é de número
    t = re.sub(r"\s+", " ", t).strip()
    return tools._numwords_to_digits(t)  # noqa: SLF001 - "cinco milhas" -> "5 milhas"


def convert(value: float, src: str, dst: str) -> Optional[float]:
    """Converte entre unidades da mesma grandeza. None = grandezas diferentes (ex.: metros em litros)."""
    if src in _TEMPS and dst in _TEMPS:
        a, b = _TEMPS[src], _TEMPS[dst]
        c = value if a == "c" else (value - 32) * 5 / 9 if a == "f" else value - 273.15
        return c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
    if src in _UNITS and dst in _UNITS and _UNITS[src][0] == _UNITS[dst][0]:
        return value * _UNITS[src][1] / _UNITS[dst][1]
    return None


def fmt_number(x: float) -> str:
    """Número em português: 8,05 / 1.609,34 / 0,0394 (casas que importam, sem zeros sobrando)."""
    ax = abs(x)
    digits = 0 if ax >= 1000 else 2 if ax >= 1 else 4
    text = f"{x:,.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def unit_name(unit: str, value: float) -> str:
    if unit in _TEMPS:
        sing, plural = _TEMP_NAMES[_TEMPS[unit]]
    else:
        _, _, sing, plural = _UNITS[unit]
    return sing if abs(value) == 1 else plural


def _parse_conversion(_norm_text: str, original: str) -> Optional[dict]:
    text = clean_phrase(original)
    for rx in (_CONV_A, _CONV_B):
        m = rx.search(text)
        if m and convert(1.0, m.group("de"), m.group("para")) is not None:
            return {"valor": _to_float(m.group("valor")), "de": m.group("de"), "para": m.group("para")}
    return None


@skill(
    name="converter_unidades",
    title="converter unidades",
    description=("Converte medidas: comprimento (km, milhas, pés, polegadas), peso (kg, libras, onças), volume "
                 "(litros, xícaras, colheres), temperatura (Celsius, Fahrenheit, Kelvin), velocidade e dados (MB, GB)."),
    permission=Permission.READ,
    public=True,
    timeout=3,
    parse=_parse_conversion,
    params={"type": "object", "required": ["valor", "de", "para"], "properties": {
        "valor": {"type": "number"},
        "de": {"type": "string", "description": "Unidade de origem (ex.: milhas, fahrenheit, xicaras)."},
        "para": {"type": "string", "description": "Unidade de destino (ex.: km, celsius, ml)."}}},
    examples=["quanto é 5 milhas em km", "converte 350 fahrenheit para celsius", "2 xícaras em ml"],
)
def converter_unidades(ctx: SkillContext, valor: float, de: str, para: str) -> SkillResult:
    from skills.workspace.layouts import norm

    src, dst = norm(de).replace(" / ", "/"), norm(para).replace(" / ", "/")
    src = de.lower() if de.lower() in _UNITS else src  # "km/h" perde a barra na normalização
    dst = para.lower() if para.lower() in _UNITS else dst
    if src not in _UNITS and src not in _TEMPS or dst not in _UNITS and dst not in _TEMPS:
        return SkillResult(ok=False, speech="Não conheço uma dessas unidades, senhor.")
    out = convert(float(valor), src, dst)
    if out is None:
        return SkillResult(ok=False, speech="Essas medidas não se convertem uma na outra, senhor.")
    left = f"{fmt_number(valor)} {unit_name(src, valor)}"
    right = f"{fmt_number(out)} {unit_name(dst, out)}"
    verb = "é" if abs(valor) == 1 else "são"
    return SkillResult(speech=f"{left} {verb} {right}.", data={"resultado": out},
                       cards=[{"type": "skill", "data": {"tag": "CONVERSÃO", "source": "na hora, sem internet",
                                                         "rows": [{"label": left, "value": f"= {right}"}]}}])


# ------------------------------------------------------------------ senha forte
SYMBOLS = "!@#$%&*-_=+?"


def make_password(length: int = 20) -> str:
    """Senha aleatória (secrets) com maiúscula, minúscula, número e símbolo; sem caracteres que confundem (O0Il1)."""
    length = max(12, min(64, int(length)))
    upper = "".join(c for c in string.ascii_uppercase if c not in "OI")
    lower = "".join(c for c in string.ascii_lowercase if c != "l")
    digits = "".join(c for c in string.digits if c not in "01")
    pools = [upper, lower, digits, SYMBOLS]
    chars = [secrets.choice(p) for p in pools]
    everything = "".join(pools)
    chars += [secrets.choice(everything) for _ in range(length - len(chars))]
    for i in range(len(chars) - 1, 0, -1):  # embaralha (Fisher-Yates com secrets)
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


@skill(
    name="gerar_senha",
    title="gerar uma senha",
    description="Gera uma senha forte e aleatória e copia para a área de transferência do PC (nunca fala a senha).",
    permission=Permission.ACTION,
    llm=False,  # a senha não passa pela IA
    allow_remote=False,  # vai para a área de transferência do PC
    timeout=5,
    triggers=[r"\b(?:gera|gere|gerar|cria|crie|criar|faz|faca|inventa|inventar|me da)\s+(?:uma\s+)?(?:nova\s+)?senha"
              r"(?:\s+(?:forte|segura|aleatoria|boa))?(?:\s+(?:de|com)\s+(?P<tamanho>\d{1,2})\s+(?:caracteres|letras|digitos))?\b"],
    params={"type": "object", "properties": {"tamanho": {"type": "integer", "description": "12 a 64 caracteres."}}},
    examples=["gera uma senha forte", "cria uma senha de 16 caracteres"],
)
def gerar_senha(ctx: SkillContext, tamanho: int = 20) -> SkillResult:
    from skills.clipboard_ai import write_clipboard

    size = max(12, min(64, int(tamanho or 20)))
    if not write_clipboard(make_password(size)):
        return SkillResult(ok=False, speech="Não consegui copiar a senha para a área de transferência, senhor. Isso só "
                                            "funciona no próprio PC com Windows.")
    return SkillResult(speech=f"Pronto, senhor: copiei uma senha forte de {size} caracteres. É só colar; eu não "
                              "guardo nem falo a senha.")
