import unicodedata
from typing import List, Dict, Optional

def normalize_header(text: str) -> str:
    """
    Normalizes a table header string to a canonical form.
    - Lowercase
    - Remove accents
    - Remove punctuation
    - Trim whitespace
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove accents (NFKD normalization)
    text = "".join(
        c for c in unicodedata.normalize('NFKD', text)
        if unicodedata.category(c) != 'Mn'
    )

    # Remove punctuation (keep only alphanumeric and space)
    import re
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # Trim redundant whitespace
    text = " ".join(text.split())

    return text

# Canonical targets and their aliases
HEADER_ALIASES: Dict[str, List[str]] = {
    "unit_price": [
        "preco unitario", "preco unit", "valor unitario", "valor unit",
        "vlr unitario", "vlr unit", "vlt unit", "vlt und", "vlr und",
        "valor und", "preco und", "p unit", "p unitario", "unitario", "unit"
    ],
    "quantity": [
        "quantidade", "qtde", "quant", "qtd"
    ],
    "total_price": [
        "valor total", "vlr total", "preco total", "total", "vlt total"
    ],
    "description": [
        "descricao", "item", "produto", "especificacao"
    ],
}

def identify_column_role(header_text: str) -> Optional[str]:
    """
    Identifies the role of a column based on its normalized header text.
    """
    normalized = normalize_header(header_text)
    for role, aliases in HEADER_ALIASES.items():
        if normalized in aliases or any(alias in normalized for alias in aliases):
            return role
    return None
