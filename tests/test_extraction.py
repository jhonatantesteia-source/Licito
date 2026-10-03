import pytest
from pathlib import Path
from licitacoes.edital.deterministic_parser import DeterministicParser

def test_edital_054_extraction():
    parser = DeterministicParser()
    # Path to the MD file in exemplos/
    path = Path("exemplos/DL Nº 054- edital aquisição de generos alimenticios praça da alegria.md")
    items = parser.parse(path)

    assert len(items) == 19, f"Esperado 19 itens, encontrado {len(items)}"

    # Item 1 check: ALHO, CABEÇA INTEIRA... 1 KG, teto R$ 31,51
    item1 = items[0]
    assert "ALHO" in item1['description'].upper()
    assert item1['unit'] == "KG"
    assert item1['ceiling_price'] == 3151

    # Item 19 check: SALSICHA CONGELADA... 200 KG, teto R$ 12,67
    item19 = items[-1]
    assert "SALSICHA" in item19['description'].upper()
    assert item19['quantity'] == 200
    assert item19['ceiling_price'] == 1267

    total = sum(item['quantity'] * item['ceiling_price'] for item in items)
    # R$ 26.752,96 = 2675296 cents
    assert total == 2675296, f"Total esperado 2675296, encontrado {total}"
