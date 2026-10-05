"""Banco SQLite local: licitações, itens do edital e proposta (marca/preço).

- Caminho absoluto em BASE_DIR/data/licitacoes.db
- Valores em centavos (INTEGER)
- Uma conexão por operação (o Streamlit reexecuta o script a cada clique)
- PRAGMA user_version controla migrações
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from licitacoes.config import DATA_DIR

SCHEMA_VERSION = 1
DEFAULT_DB = DATA_DIR / "licitacoes.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _migrate(conn: sqlite3.Connection) -> None:
    v = conn.execute("PRAGMA user_version").fetchone()[0]
    if v < 1:
        conn.executescript(
            """
            CREATE TABLE tender (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                organ TEXT, process_number TEXT, modality TEXT,
                estimated_total_cents INTEGER,
                deadlines_json TEXT NOT NULL DEFAULT '{}',
                edital_sha256 TEXT, edital_path TEXT,
                extraction_method TEXT NOT NULL DEFAULT 'deterministic',
                needs_review INTEGER NOT NULL DEFAULT 0,
                current_step TEXT NOT NULL DEFAULT 'edital',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER NOT NULL REFERENCES tender(id) ON DELETE CASCADE,
                number INTEGER NOT NULL,
                description TEXT NOT NULL, unit TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL,
                ceiling_cents INTEGER,
                position INTEGER NOT NULL,
                UNIQUE (tender_id, number)
            );
            CREATE TABLE proposal (
                tender_id INTEGER NOT NULL,
                item_number INTEGER NOT NULL,
                brand TEXT NOT NULL DEFAULT '',
                proposed_cents INTEGER,
                PRIMARY KEY (tender_id, item_number),
                FOREIGN KEY (tender_id, item_number) REFERENCES item(tender_id, number) ON DELETE CASCADE
            );
            CREATE INDEX idx_item_tender ON item(tender_id, position);
            """
        )
        conn.execute("PRAGMA user_version = 1")

    if v < 2:
        conn.executescript(
            """
            CREATE TABLE competitor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER NOT NULL REFERENCES tender(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE competitor_file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER NOT NULL REFERENCES competitor(id) ON DELETE CASCADE,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            CREATE INDEX idx_competitor_tender ON competitor(tender_id);
            """
        )
        conn.execute("PRAGMA user_version = 2")

    if v < 3:
        conn.executescript(
            """
            CREATE TABLE competitor_proposal (
                competitor_id INTEGER NOT NULL REFERENCES competitor(id) ON DELETE CASCADE,
                item_number INTEGER NOT NULL,
                proposed_cents INTEGER,
                brand TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (competitor_id, item_number)
            );
            """
        )
        conn.execute("PRAGMA user_version = 3")


@contextmanager
def connect(db_path: str | Path | None = None):
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _migrate(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------ utilidades de conversão
def to_decimal(value: Any) -> Decimal | None:
    """Converte valor do banco (TEXT ou INTEGER cents) para Decimal."""
    if value is None:
        return None
    try:
        if isinstance(value, int):
            # Se for int, assumimos centavos (legado)
            return (Decimal(value) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        # Se for string, assume-se representação decimal "31.99"
        return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None

def from_decimal(value: Decimal | None) -> str | None:
    """Converte Decimal para string para persistência em TEXT."""
    if value is None:
        return None
    # Retorna "31.99"
    return str(value.quantize(Decimal("0.01"), ROUND_HALF_UP))
def create_tender(name: str, items, *, organ=None, process_number=None, modality=None,
                  estimated_total_cents=None, deadlines: dict | None = None, edital_sha256=None,
                  edital_path=None, extraction_method="deterministic", needs_review=False,
                  db_path=None) -> int:
    """Cria a licitação e seus itens (na ordem do edital). Devolve o id."""
    now = _now()
    with connect(db_path) as c:
        cur = c.execute(
            """INSERT INTO tender (name, organ, process_number, modality, estimated_total_cents,
               deadlines_json, edital_sha256, edital_path, extraction_method, needs_review,
               current_step, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,'proposta',?,?)""",
            (name, organ, process_number, modality, estimated_total_cents,
             json.dumps(deadlines or {}, ensure_ascii=False), edital_sha256,
             str(edital_path) if edital_path else None, extraction_method, int(needs_review), now, now))
        tid = cur.lastrowid
        c.executemany(
            "INSERT INTO item (tender_id, number, description, unit, quantity, ceiling_cents, position) "
            "VALUES (?,?,?,?,?,?,?)",
            [(tid, i.number, i.description, i.unit, i.quantity, i.ceiling_cents, i.position) for i in items])
        return tid


def find_tender_by_sha(sha256: str, db_path=None):
    with connect(db_path) as c:
        r = c.execute("SELECT * FROM tender WHERE edital_sha256=? ORDER BY id DESC LIMIT 1", (sha256,)).fetchone()
        return dict(r) if r else None


def get_tender(tender_id: int, db_path=None):
    with connect(db_path) as c:
        r = c.execute("SELECT * FROM tender WHERE id=?", (tender_id,)).fetchone()
        return dict(r) if r else None


def list_tenders(include_archived=False, db_path=None) -> list[dict]:
    q = "SELECT * FROM tender" + ("" if include_archived else " WHERE archived=0") + " ORDER BY updated_at DESC, id DESC"
    with connect(db_path) as c:
        return [dict(r) for r in c.execute(q)]


def set_step(tender_id: int, step: str, db_path=None) -> None:
    with connect(db_path) as c:
        c.execute("UPDATE tender SET current_step=?, updated_at=? WHERE id=?", (step, _now(), tender_id))


def archive_tender(tender_id: int, archived=True, db_path=None) -> None:
    with connect(db_path) as c:
        c.execute("UPDATE tender SET archived=?, updated_at=? WHERE id=?", (int(archived), _now(), tender_id))


def delete_tender(tender_id: int, db_path=None) -> None:
    with connect(db_path) as c:
        c.execute("DELETE FROM tender WHERE id=?", (tender_id,))


# ------------------------------------------------------------ concorrentes
def create_competitor(tender_id: int, name: str, db_path=None) -> int:
    """Cria um concorrente para uma licitação. Devolve o id."""
    now = _now()
    with connect(db_path) as c:
        cur = c.execute(
            "INSERT INTO competitor (tender_id, name, created_at) VALUES (?,?,?)",
            (tender_id, name, now))
        return cur.lastrowid


def add_competitor_file(competitor_id: int, file_name: str, file_path: str, db_path=None) -> None:
    """Associa um arquivo a um concorrente."""
    now = _now()
    with connect(db_path) as c:
        c.execute(
            "INSERT INTO competitor_file (competitor_id, file_name, file_path, uploaded_at) VALUES (?,?,?,?)",
            (competitor_id, file_name, file_path, now))


def list_competitors(tender_id: int, db_path=None) -> list[dict]:
    """Lista todos os concorrentes de uma licitação."""
    with connect(db_path) as c:
        rows = c.execute(
            "SELECT id, name, created_at FROM competitor WHERE tender_id=? ORDER BY name",
            (tender_id,)).fetchall()
        return [dict(r) for r in rows]


def get_competitor_files(competitor_id: int, db_path=None) -> list[dict]:
    """Lista os arquivos de um concorrente específico."""
    with connect(db_path) as c:
        rows = c.execute(
            "SELECT id, file_name, file_path, uploaded_at FROM competitor_file WHERE competitor_id=?",
            (competitor_id,)).fetchall()
        return [dict(r) for r in rows]


def delete_competitor(competitor_id: int, db_path=None) -> None:
    """Remove um concorrente (e seus arquivos via CASCADE)."""
    with connect(db_path) as c:
        c.execute("DELETE FROM competitor WHERE id=?", (competitor_id,))


def save_competitor_proposal(competitor_id: int, rows, db_path=None) -> None:
    """
    rows: iterável de (item_number, proposed_cents|None, brand).
    """
    with connect(db_path) as c:
        c.executemany(
            """INSERT INTO competitor_proposal (competitor_id, item_number, brand, proposed_cents) VALUES (?,?,?,?)
               ON CONFLICT(competitor_id, item_number) DO UPDATE
               SET brand=excluded.brand, proposed_cents=excluded.proposed_cents""",
            [(competitor_id, n, (b or "").strip(), p) for n, p, b in rows])


def get_competitor_proposal(competitor_id: int, db_path=None) -> list[dict]:
    """Retorna a proposta de um concorrente específico."""
    with connect(db_path) as c:
        rows = c.execute(
            "SELECT item_number, proposed_cents, brand FROM competitor_proposal WHERE competitor_id=?",
            (competitor_id,)).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------ itens e proposta
def get_items(tender_id: int, db_path=None) -> list[dict]:
    """Itens na ordem do edital, já com marca e preço proposto (se houver)."""
    with connect(db_path) as c:
        rows = c.execute(
            """SELECT i.number, i.description, i.unit, i.quantity, i.ceiling_cents, i.position,
                      COALESCE(p.brand,'') AS brand, p.proposed_cents AS proposed_cents
               FROM item i LEFT JOIN proposal p
                 ON p.tender_id=i.tender_id AND p.item_number=i.number
               WHERE i.tender_id=? ORDER BY i.position""", (tender_id,)).fetchall()
        return [dict(r) for r in rows]


def save_proposal(tender_id: int, item_number: int, proposed_cents: int | None, brand: str = "", db_path=None):
    save_proposal_bulk(tender_id, [(item_number, proposed_cents, brand)], db_path)


def save_proposal_bulk(tender_id: int, rows, db_path=None) -> None:
    """rows: iterável de (item_number, proposed_cents|None, brand)."""
    with connect(db_path) as c:
        c.executemany(
            """INSERT INTO proposal (tender_id, item_number, brand, proposed_cents) VALUES (?,?,?,?)
               ON CONFLICT(tender_id, item_number) DO UPDATE
               SET brand=excluded.brand, proposed_cents=excluded.proposed_cents""",
            [(tender_id, n, (b or "").strip(), p) for n, p, b in rows])
        c.execute("UPDATE tender SET updated_at=? WHERE id=?", (_now(), tender_id))


def counts(db_path=None) -> dict:
    """Contagens para a página de Diagnóstico."""
    with connect(db_path) as c:
        return {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("tender", "item", "proposal")}
