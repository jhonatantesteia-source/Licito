import sqlite3
import json
from pathlib import Path
from licitacoes.config import BASE_DIR

DB_PATH = BASE_DIR / "data" / "licitacoes.db"

class PersistenceService:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def init_db():
        with PersistenceService.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    organ TEXT,
                    process_number TEXT,
                    estimated_total INTEGER,
                    edital_sha256 TEXT,
                    extraction_method TEXT,
                    needs_review BOOLEAN,
                    current_step TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    description TEXT,
                    unit TEXT,
                    quantity REAL,
                    ceiling_price INTEGER,
                    position INTEGER,
                    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    tender_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    proposed_price INTEGER,
                    brand TEXT,
                    PRIMARY KEY (tender_id, item_id),
                    FOREIGN KEY (tender_id) REFERENCES tenders(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    @staticmethod
    def save_tender(tender_data, items):
        with PersistenceService.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tenders (name, organ, process_number, estimated_total, extraction_method) VALUES (?, ?, ?, ?, ?)",
                (tender_data['name'], tender_data.get('organ'), tender_data.get('process_number'), tender_data.get('estimated_total', 0), tender_data.get('extraction_method'))
            )
            tender_id = cursor.lastrowid
            for pos, item in enumerate(items):
                cursor.execute(
                    "INSERT INTO items (tender_id, item_id, description, unit, quantity, ceiling_price, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tender_id, item['id'], item['description'], item['unit'], item['quantity'], item['ceiling_price'], pos)
                )
            conn.commit()
            return tender_id

    @staticmethod
    def get_tender_items(tender_id):
        with PersistenceService.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM items WHERE tender_id = ? ORDER BY position", (tender_id,)).fetchall()]

    @staticmethod
    def save_proposal_item(tender_id, item_id, price, brand):
        with PersistenceService.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO proposals (tender_id, item_id, proposed_price, brand) VALUES (?, ?, ?, ?)",
                (tender_id, item_id, price, brand)
            )
            conn.commit()
