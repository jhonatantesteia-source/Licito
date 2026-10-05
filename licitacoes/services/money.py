"""Dinheiro sempre em CENTAVOS (int). Nunca float."""
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

_BR = re.compile(r"^\d{1,3}(\.\d{3})+(,\d+)?$|^\d+(,\d+)?$")   # 1.234,56 | 31,51 | 11
_EN = re.compile(r"^\d+\.\d{1,2}$")                              # 31.51


def parse_brl_to_cents(text) -> int | None:
    """'R$ 1.234,56' -> 123456 ; '31,51' -> 3151 ; '11' -> 1100 ; inválido -> None."""
    if text is None:
        return None
    s = str(text).replace("\\", "").replace("R$", "").replace("r$", "")
    s = re.sub(r"\s+", "", s).strip("*")
    if not s:
        return None
    if _BR.match(s):
        s = s.replace(".", "").replace(",", ".")
    elif not _EN.match(s):
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    if d < 0:
        return None
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_brl(cents: int | None) -> str:
    """123456 -> 'R$ 1.234,56' (sem float)."""
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    reais, cent = divmod(cents, 100)
    return f"{sign}R$ {reais:,}".replace(",", ".") + f",{cent:02d}"


def format_plain(cents: int | None) -> str:
    """3151 -> '31,51' (para campos de edição)."""
    if cents is None:
        return ""
    reais, cent = divmod(int(cents), 100)
    return f"{reais},{cent:02d}"
