import pandas as pd
import re
import pymupdf
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
        try:
            with pymupdf.open(path) as doc:
                for page in doc:
                    tabs = page.find_tables()
                    for tab in tabs:
                        df = tab.to_pandas()
                        # Tenta identificar a linha de cabeçalho
                        header_idx = -1
                        for i, row in df.iterrows():
                            row_str = " ".join(map(str, row)).upper()
                            if "ITEM" in row_str and ("QTDE" in row_str or "QUANTIDADE" in row_str):
                                header_idx = i
                                break

                        if header_idx == -1: continue

                        # Define o cabeçalho real e remove as linhas acima dele
                        df.columns = df.iloc[header_idx]
                        df = df.iloc[header_idx + 1:].reset_index(drop=True)

                        for _, row in df.iterrows():
                            # Tenta encontrar a coluna de valor unitário dinamicamente
                            # Procuramos por 'VALOR', 'PREÇO' ou 'UNITÁRIO' no cabeçalho
                            val_col_idx = -1
                            for idx, col_name in enumerate(df.columns):
                                col_name_up = str(col_name).upper()
                                if "UNIT" in col_name_up or "VALOR" in col_name_up or "PREÇO" in col_name_up:
                                    val_col_idx = idx
                                    break

                            # Fallback para a coluna 4 se não encontrar nome
                            if val_col_idx == -1: val_col_idx = 4

                            cols = row.values
                            if len(cols) < 4 or pd.isna(cols[0]): continue

                            # Tenta pegar o valor da coluna identificada
                            price_val = cols[val_col_idx] if len(cols) > val_col_idx else cols[-1]

                            items.append({
                                "id": str(cols[0]),
                                "description": str(cols[1]),
                                "unit": str(cols[2]),
                                "quantity": float(str(cols[3]).replace(",", ".")),
                                "ceiling_price": self.parse_money(str(price_val))
                            })
        except Exception as e:
            print(f"Erro ao ler PDF {path}: {e}")
        return items

    def extract_from_md(self, path: Path) -> List[Dict]:
        items = []
        text = path.read_text(encoding="utf-8")
        # Procura por tabelas markdown | ITEM | ... |
        table_pattern = re.compile(r"\|.*\|", re.MULTILINE)
        lines = table_pattern.findall(text)

        for line in lines:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if not cols or "ITEM" in cols[0].upper() or "---" in cols[0]: continue
            if len(cols) >= 5:
                try:
                    items.append({
                        "id": cols[0],
                        "description": cols[1],
                        "unit": cols[2],
                        "quantity": float(cols[3].replace(",", ".")),
                        "ceiling_price": self.parse_money(cols[4])
                    })
                except ValueError:
                    continue
        return items

    def extract_from_docx(self, path: Path) -> List[Dict]:
        items = []
        doc = Document(path)
        for table in doc.tables:
            for i, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                if i == 0 or "ITEM" in cells[0].upper(): continue
                if len(cells) >= 5:
                    try:
                        items.append({
                            "id": cells[0],
                            "description": cells[1],
                            "unit": cells[2],
                            "quantity": float(cells[3].replace(",", ".")),
                            "ceiling_price": self.parse_money(cells[4])
                        })
                    except ValueError:
                        continue
        return items

    def extract_from_xlsx(self, path: Path) -> List[Dict]:
        items = []
        try:
            # Lê todas as abas do Excel
            all_sheets = pd.read_excel(path, sheet_name=None)
            for sheet_name, df in all_sheets.items():
                # Tenta identificar a linha de cabeçalho
                header_idx = -1
                for i, row in df.iterrows():
                    row_str = " ".join(map(str, row)).upper()
                    if "ITEM" in row_str and ("QTDE" in row_str or "QUANTIDADE" in row_str):
                        header_idx = i
                        break

                if header_idx == -1: continue

                # Define o cabeçalho real e remove as linhas acima dele
                df.columns = df.iloc[header_idx]
                df = df.iloc[header_idx + 1:].reset_index(drop=True)

                for _, row in df.iterrows():
                    # Tenta extrair os dados baseado na posição ou nome da coluna
                    # Esperamos: Item, Descrição, Unid, Qtde, Valor Unitário
                    cols = row.values
                    if len(cols) < 5 or pd.isna(cols[0]): continue
                    items.append({
                        "id": str(cols[0]),
                        "description": str(cols[1]),
                        "unit": str(cols[2]),
                        "quantity": float(str(cols[3]).replace(",", ".")),
                        "ceiling_price": self.parse_money(str(cols[4]))
                    })
        except Exception as e:
            print(f"Erro ao ler XLSX {path}: {e}")
        return items

    def parse(self, path: Path) -> List[Dict]:
        suffix = path.suffix.lower()
        if suffix == ".pdf": return self.extract_from_pdf(path)
        if suffix == ".md": return self.extract_from_md(path)
        if suffix == ".docx": return self.extract_from_docx(path)
        if suffix in [".xlsx", ".xls"]: return self.extract_from_xlsx(path)
        return []
