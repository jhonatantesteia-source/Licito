from pathlib import Path

import pytest

from licitacoes.edital.items_parser import parse_edital
from licitacoes.services.money import format_brl

FX = Path(__file__).parent / "fixtures" / "editais"
TOTAL = 2675296  # R$ 26.752,96


def _check(res):
    assert len(res.items) == 19
    assert [i.number for i in res.items] == list(range(1, 20))      # mesma ordem do edital
    assert [i.position for i in res.items] == list(range(19))
    a, z = res.items[0], res.items[-1]
    assert (a.unit, a.quantity, a.ceiling_cents) == ("KG", 1, 3151)
    assert a.description.startswith("ALHO, CABEÇA INTEIRA")
    assert (z.unit, z.quantity, z.ceiling_cents) == ("KG", 200, 1267)
    assert z.description.startswith("SALSICHA CONGELADA") and z.description.endswith("NA EMBALAGEM.")
    assert res.computed_total_cents == TOTAL
    assert res.estimated_total_cents == TOTAL
    assert not res.warnings and not res.needs_review


def test_md():
    _check(parse_edital(FX / "edital_054_2026.md"))


def test_docx():
    _check(parse_edital(FX / "edital_054_2026.docx"))


def test_pdf(tmp_path):
    """PDF sintético com a mesma tabela (grade com linhas), gerado a partir dos itens lidos do .md."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    src = parse_edital(FX / "edital_054_2026.md")
    st = ParagraphStyle("s", fontName="Helvetica", fontSize=7, leading=8.5)
    rows = [["ITEM", "ESPECIFICAÇÕES", "UNID.", "QTDE", "VLT UND MAXIMO"]]
    for i in src.items:
        rows.append([str(i.number), Paragraph(i.description, st), i.unit, str(i.quantity),
                     f"{i.ceiling_cents // 100},{i.ceiling_cents % 100:02d}"])
    rows.append(["VALOR TOTAL", "", "", "", ""])
    t = Table(rows, colWidths=[40, 520, 40, 40, 80], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    pdf = tmp_path / "edital.pdf"
    SimpleDocTemplate(str(pdf), pagesize=landscape(A4)).build(
        [Paragraph("VALOR ESTIMADO DA CONTRATAÇÃO: R$ 26.752,96", st), t])
    res = parse_edital(pdf)                                         # tabela quebra em 2+ páginas
    assert len(res.items) == 19 and res.computed_total_cents == TOTAL
    assert [i.description for i in res.items] == [i.description for i in src.items]  # sem truncar


def test_erro_de_digitacao_do_edital_e_mantido():
    res = parse_edital(FX / "edital_054_2026.md")
    assert "EMBALEGEM" in res.items[1].description                  # não "corrige" o edital


def test_sem_tabela_nao_inventa(tmp_path):
    f = tmp_path / "vazio.md"
    f.write_text("# Edital sem tabela de itens\n\nTexto qualquer.", encoding="utf-8")
    res = parse_edital(f)
    assert res.items == [] and res.needs_review and res.warnings


def test_total_diferente_do_estimado_gera_aviso(tmp_path):
    f = tmp_path / "e.md"
    f.write_text("VALOR ESTIMADO DA CONTRATAÇÃO: R\\$ 100,00\n\n"
                 "| ITEM | ESPECIFICAÇÕES | UNID. | QTDE | VLT UND MAXIMO |\n| --- | --- | --- | --- | --- |\n"
                 "| 1 | ARROZ | KG | 2 | 10,00 |\n| **VALOR TOTAL** | | | | |\n", encoding="utf-8")
    res = parse_edital(f)
    assert res.computed_total_cents == 2000 and res.needs_review
    assert "difere do valor estimado" in res.warnings[0]


def test_formato_nao_suportado(tmp_path):
    f = tmp_path / "x.xyz"
    f.write_text("a")
    assert parse_edital(f).warnings
