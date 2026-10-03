import pandas as pd
import re
import fitz
from docx import Document
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal

class DeterministicParser:
    """Parser determinístico para Anexo I (Tabelas de Preços)."""

    @staticmethod
    def parse_money(value: str) -> int:
        if not value or value == "-": return 0
        # Remove R$, pontos de milhar, troca vírgula por ponto
        clean = value.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return int(Decimal(clean) * 100)
        except:
            return 0

    def extract_from_pdf(self, path: Path) -> List[Dict]:
        items = []
        with fitz.open(path) as doc:
            for page in doc:
                tabs = page.find_tables()
                for tab in tabs:
                    df = tab.to_pandas()
                    # Tenta identificar a linha de cabeçalho
                    header_idx = -1
                    for i, row in df.iterrows():
                        row_str = " ".join(map(str, row)).upper()
                        if "ITEM" in row_str and "QTDE" in row_str:
                            header_idx = i
                            break

                    if header_idx == -1: continue

                    for i in range(header_idx + 1, len(df)):
                        row = df.iloc[i]
                        if len(row) < 4 or pd.isna(row[0]): continue
                        items.append({
                            "id": str(row[0]),
                            "description": str(row[1]),
                            "unit": str(row[2]),
                            "quantity": float(str(row[3]).replace(",", ".")),
                            "ceiling_price": self.parse_money(str(row[4])) if len(row) > 4 else 0
                        })
        return items

    def extract_from_md(self, path: Path) -> List[Dict]:
        items = []
        text = path.read_text(encoding="utf-8")
        # Procura por tabelas markdown | ITEM | ... |
        table_pattern = re.compile(r"\|.*\|", re.MULTILINE)
        lines = table_pattern.findall(text)

        for line in lines:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if not cols or "ITEM" in cols[0].upper(): continue
            if len(cols) >= 5:
                items.append({
                    "id": cols[0],
                    "description": cols[1],
                    "unit": cols[2],
                    "quantity": float(cols[3].replace(",", ".")),
                    "ceiling_price": self.parse_money(cols[4])
                })
        return items

    def extract_from_docx(self, path: Path) -> List[Dict]:
        items = []
        doc = Document(path)
        for table in doc.tables:
            for i, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                if i == 0 or "ITEM" in cells[0].upper(): continue
                if len(cells) >= 5:
                    items.append({
                        "id": cells[0],
                        "description": cells[1],
                        "unit": cells[2],
                        "quantity": float(cells[3].replace(",", ".")),
                        "ceiling_price": self.parse_money(cells[4])
                    })
        return items

    def parse(self, path: Path) -> List[Dict]:
        suffix = path.suffix.lower()
        if suffix == ".pdf": return self.extract_from_pdf(path)
        if suffix == ".md": return self.extract_from_md(path)
        if suffix == ".docx": return self.extract_from_docx(path)
        return []
