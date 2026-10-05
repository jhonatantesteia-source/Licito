import sqlite3
from pathlib import Path

import pytest

from licitacoes.edital.items_parser import parse_edital
from licitacoes.services import persistence as db
from licitacoes.services.proposal_calc import summarize

FX = Path(__file__).parent / "fixtures" / "editais" / "edital_054_2026.md"


@pytest.fixture()
def dbp(tmp_path):
    return tmp_path / "t.db"


def _novo(dbp):
    r = parse_edital(FX)
    return db.create_tender("Dispensa 054/2026", r.items, estimated_total_cents=r.estimated_total_cents,
                            edital_sha256=r.sha256, db_path=dbp), r


def test_cria_e_le_itens_na_ordem(dbp):
    tid, r = _novo(dbp)
    its = db.get_items(tid, dbp)
    assert [i["number"] for i in its] == list(range(1, 20))
    assert its[0]["ceiling_cents"] == 3151 and its[18]["quantity"] == 200
    assert db.get_tender(tid, dbp)["estimated_total_cents"] == 2675296


def test_proposta_persiste_apos_reabrir(dbp):
    tid, _ = _novo(dbp)
    db.save_proposal_bulk(tid, [(1, 2900, "Marca X"), (16, 850, "Guaraná Y")], dbp)
    # "reinicia o app": nova conexão a partir do arquivo
    its = {i["number"]: i for i in db.get_items(tid, dbp)}
    assert its[1]["proposed_cents"] == 2900 and its[1]["brand"] == "Marca X"
    assert its[16]["proposed_cents"] == 850
    assert its[2]["proposed_cents"] is None
    db.save_proposal(tid, 1, 2800, "Marca Z", dbp)                  # atualiza, não duplica
    assert db.get_items(tid, dbp)[0]["proposed_cents"] == 2800
    assert db.counts(dbp)["proposal"] == 2


def test_resumo_acima_do_teto(dbp):
    tid, _ = _novo(dbp)
    db.save_proposal_bulk(tid, [(16, 850, "x"), (1, 3000, "")], dbp)    # item 16: teto 7,71 -> acima
    s = summarize(db.get_items(tid, dbp))
    assert s["above_ceiling"] == [16]
    assert s["total_proposed_cents"] == 800 * 850 + 1 * 3000
    assert s["total_ceiling_cents"] == 2675296
    assert 1 in s["missing_brand"] and 2 in s["missing_price"]


def test_arquivar_e_listar(dbp):
    tid, _ = _novo(dbp)
    assert len(db.list_tenders(db_path=dbp)) == 1
    db.archive_tender(tid, True, dbp)
    assert db.list_tenders(db_path=dbp) == []
    assert len(db.list_tenders(include_archived=True, db_path=dbp)) == 1


def test_evita_duplicar_pelo_hash(dbp):
    tid, r = _novo(dbp)
    assert db.find_tender_by_sha(r.sha256, dbp)["id"] == tid


def test_chaves_estrangeiras_e_versao(dbp):
    tid, _ = _novo(dbp)
    with db.connect(dbp) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
        with pytest.raises(sqlite3.IntegrityError):                    # item inexistente
            c.execute("INSERT INTO proposal (tender_id,item_number,brand,proposed_cents) VALUES (?,?,?,?)", (tid, 99, "", 1))
    db.delete_tender(tid, dbp)                                          # cascata
    assert db.counts(dbp) == {"tender": 0, "item": 0, "proposal": 0}
