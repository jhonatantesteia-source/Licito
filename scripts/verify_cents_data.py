import sqlite3
from decimal import Decimal
from pathlib import Path
from licitacoes.config import DATA_DIR

DB_PATH = DATA_DIR / "licitacoes.db"

def verify_column(conn, table, column):
    print(f"\nVerifying {table}.{column}...")
    rows = conn.execute(f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
    if not rows:
        print("No data found.")
        return

    count = 0
    for row in rows:
        val = row[0]
        try:
            # Premise: val is integer cents
            decimal_val = Decimal(val) / 100
            formatted = "{:.2f}".format(decimal_val)
            print(f"Value: {val} -> Decimal: {decimal_val} -> String: {formatted}")
            count += 1
        except Exception as e:
            print(f"Error processing value {val}: {e}")
    print(f"Verified {count} records in {table}.{column}")

def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        verify_column(conn, "tender", "estimated_total_cents")
        verify_column(conn, "item", "ceiling_cents")
        verify_column(conn, "proposal", "proposed_cents")
        verify_column(conn, "competitor_proposal", "proposed_cents")

if __name__ == "__main__":
    main()
