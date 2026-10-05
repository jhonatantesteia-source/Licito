"""Cálculos da proposta (puros, sem tela e sem banco). Tudo em centavos."""
from __future__ import annotations


def line_total(quantity: int, cents: int | None) -> int | None:
    return None if cents is None else quantity * cents


def status(ceiling_cents: int | None, proposed_cents: int | None) -> str:
    """'falta' | 'ok' | 'acima' (acima do preço máximo = desclassificação)."""
    if proposed_cents is None:
        return "falta"
    if ceiling_cents is not None and proposed_cents > ceiling_cents:
        return "acima"
    return "ok"


def summarize(items: list[dict]) -> dict:
    """items: saída de persistence.get_items()."""
    total_prop = total_ceiling = 0
    acima, faltam, sem_marca = [], [], []
    for it in items:
        if it["ceiling_cents"] is not None:
            total_ceiling += it["quantity"] * it["ceiling_cents"]
        s = status(it["ceiling_cents"], it["proposed_cents"])
        if s == "acima":
            acima.append(it["number"])
        elif s == "falta":
            faltam.append(it["number"])
        if it["proposed_cents"] is not None:
            total_prop += it["quantity"] * it["proposed_cents"]
            if not it["brand"].strip():
                sem_marca.append(it["number"])
    return {"total_proposed_cents": total_prop, "total_ceiling_cents": total_ceiling,
            "above_ceiling": acima, "missing_price": faltam, "missing_brand": sem_marca}
