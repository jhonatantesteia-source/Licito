from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
import re

def parse_brl(value: Any) -> Optional[Decimal]:
    """
    Parses a monetary value in Brazilian Real (BRL) format to Decimal.

    Supported formats:
    - "31,99" -> Decimal("31.99")
    - "1.250,00" -> Decimal("1250.00")
    - "R$ 31,99" -> Decimal("31.99")
    - "R$ 1.250,00" -> Decimal("1250.00")
    - "31.99" -> Decimal("31.99")
    - "1,250.00" -> Decimal("1250.00")
    - "10" -> Decimal("10.00")
    - "10,0" -> Decimal("10.00")
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Clean string: remove R$, whitespace, and other currency symbols
    val_str = str(value).replace("R$", "").strip()

    if not val_str or val_str == "-":
        return None

    # Heuristic to determine decimal separator
    # Case 1: Both dot and comma exist (e.g., 1.250,00 or 1,250.00)
    if "." in val_str and "," in val_str:
        dot_pos = val_str.rfind(".")
        comma_pos = val_str.rfind(",")
        if comma_pos > dot_pos: # BR format: 1.250,00
            clean = val_str.replace(".", "").replace(",", ".")
        else: # US format: 1,250.00
            clean = val_str.replace(",", "")

    # Case 2: Only comma exists
    elif "," in val_str:
        # If comma is at position -3 (e.g., 31,99), it's definitely decimal
        # If there's only one comma and it's not at -3, it might be a thousand separator
        # but in BRL context, a single comma is almost always the decimal separator.
        clean = val_str.replace(",", ".")

    # Case 3: Only dot exists
    elif "." in val_str:
        # Check if it's a decimal separator (position -3) or thousand separator
        if val_str.rfind(".") == len(val_str) - 3:
            clean = val_str # already dot
        else:
            clean = val_str.replace(".", "")

    # Case 4: No separators
    else:
        clean = val_str

    try:
        # Final cleaning: remove any remaining non-digit/non-dot chars
        clean = re.sub(r'[^0-9.-]', '', clean)
        return Decimal(clean).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        return None
