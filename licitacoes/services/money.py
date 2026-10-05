"""Dinheiro sempre em Decimal. Nunca float."""
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from licitacoes.ingest.money import parse_brl

def parse_brl_to_cents(text) -> int | None:
    """
    DEPRECATED: Use parse_brl from licitacoes.ingest.money instead.
    Maintained for backward compatibility during migration.
    """
    val = parse_brl(text)
    if val is None:
        return None
    return int((val * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def format_brl(val: Decimal | int | float | None) -> str:
    """
    Converts a monetary value to 'R$ 1.234,56'.
    Accepts Decimal (preferred), int (cents), or float.
    """
    if val is None:
        return ""

    # If it's an int, treat it as cents
    if isinstance(val, int):
        cents = abs(val)
        reais, cent = divmod(cents, 100)
        return f"R$ {reais:,}".replace(",", ".") + f",{cent:02d}"

    # If it's float or Decimal, treat as units
    try:
        d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return ""

    # Format Decimal to BRL string
    s = "{:,.2f}".format(d)
    # Swap dots and commas for BR format
    # 1,234.56 -> 1.234,56
    main, dec = s.rsplit(".", 1)
    main = main.replace(",", ".")
    return f"R$ {main},{dec}"

def format_plain(val: Decimal | int | float | None) -> str:
    """
    Converts a monetary value to '1.234,56' (for editing fields).
    Accepts Decimal (preferred), int (cents), or float.
    """
    if val is None:
        return ""

    if isinstance(val, int):
        reais, cent = divmod(abs(val), 100)
        return f"{reais:,}".replace(",", ".") + f",{cent:02d}"

    try:
        d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return ""

    s = "{:,.2f}".format(d)
    main, dec = s.rsplit(".", 1)
    main = main.replace(",", ".")
    return f"{main},{dec}"
