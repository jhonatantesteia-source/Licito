"""Teste de tela (Streamlit AppTest): a proposta vem do banco, sem dados inventados,
e continua lá depois de 'reiniciar' (nova sessão)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from licitacoes.edital.items_parser import parse_edital
from licitacoes.services import persistence as db

FX = Path(__file__).parent / "fixtures" / "editais" / "edital_054_2026.md"


def _app(dbp):
    def script(dbp):
        from licitacoes.ui.proposta import render_proposta_page
        render_proposta_page(db_path=dbp)
    return AppTest.from_function(script, args=(str(dbp),), default_timeout=30)


def _texto_da_tela(at) -> str:
    partes = [m.value for m in at.markdown] + [m.value for m in at.caption] + [m.value for m in at.info]
    partes += [str(m.value) for m in at.metric] + [m.value for m in at.error] + [m.value for m in at.warning]
    return " ".join(partes)


def test_sem_edital_mostra_aviso_e_nada_inventado(tmp_path):
    at = _app(tmp_path / "t.db").run()
    assert not at.exception
    assert "Ainda não há edital" in _texto_da_tela(at)
    assert "caneta" not in _texto_da_tela(at).lower()


def test_proposta_real_e_persistente(tmp_path):
    dbp = tmp_path / "t.db"
    r = parse_edital(FX)
    tid = db.create_tender("Dispensa 054/2026", r.items, estimated_total_cents=r.estimated_total_cents, db_path=dbp)
    db.save_proposal_bulk(tid, [(1, 2900, "Marca X"), (16, 850, "Guaraná Y")], dbp)

    at = _app(dbp).run()                                   # "app reiniciado": sessão nova
    assert not at.exception
    txt = _texto_da_tela(at)
    assert "caneta" not in txt.lower()
    assert "Dispensa 054/2026" in txt
    assert "R$ 26.752,96" in txt                           # total pelos preços máximos
    assert "R$ 6.829,00" in txt                            # total proposto: 800 x 8,50 + 1 x 29,00
    assert "Acima do preço máximo" in txt and "16" in txt  # item 16 passou do teto (7,71)
    assert any("Faltam preços" in w.value for w in at.warning)


def test_importar_edital_grava_no_banco_e_nao_duplica(tmp_path):
    from licitacoes.ui.proposta import import_edital_file
    dbp = tmp_path / "t.db"
    tid, res, ja = import_edital_file(FX, dbp)
    assert tid and not ja and len(res.items) == 19
    assert len(db.get_items(tid, dbp)) == 19
    tid2, _, ja2 = import_edital_file(FX, dbp)                 # mesmo arquivo de novo
    assert tid2 == tid and ja2 and db.counts(dbp)["tender"] == 1


def test_importar_arquivo_sem_tabela_nao_cria_nada(tmp_path):
    from licitacoes.ui.proposta import import_edital_file
    f = tmp_path / "x.md"; f.write_text("sem tabela", encoding="utf-8")
    tid, res, _ = import_edital_file(f, tmp_path / "t.db")
    assert tid is None and not res.items and db.counts(tmp_path / "t.db")["tender"] == 0
