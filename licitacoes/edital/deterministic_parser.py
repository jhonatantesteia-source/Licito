import pandas as pd
import re
import pymupdf
from docx import Document
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from licitacoes.ingest.money import parse_brl
from licitacoes.ingest.normalization import normalize_header, identify_column_role, HEADER_ALIASES

class DeterministicParser:
    """Parser determinístico para extração de tabelas de preços em editais e propostas."""

    def _identify_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Identifica a linha de cabeçalho baseando-se em pontuação de aliases."""
        best_idx = -1
        max_score = 0

        for i, row in df.iterrows():
            score = 0
            row_values = [str(v) for v in row.values]
            for val in row_values:
                normalized = normalize_header(val)
                for role, aliases in HEADER_ALIASES.items():
                    if normalized in aliases or any(alias in normalized for alias in aliases):
                        score += 1
                        break

            if score > max_score:
                max_score = score
                best_idx = i

        return best_idx if max_score > 0 else None

    def _infer_monetary_columns(self, df: pd.DataFrame, qty_idx: int) -> Dict[str, int]:
        """
        Tenta inferir qual coluna é unit_price e qual é total_price
        através da relação matemática: qty * unit = total.
        """
        monetary_cols = []
        for idx, col in enumerate(df.columns):
            # Testa se a coluna parece monetária em algumas linhas
            sample_vals = df.iloc[0:5, idx].dropna().astype(str)
            if any(parse_brl(v) is not None for v in sample_vals):
                monetary_cols.append(idx)

        if len(monetary_cols) < 1:
            return {}

        # Try to find a pair that satisfies qty * unit = total
        for unit_idx in monetary_cols:
            for total_idx in monetary_cols:
                if unit_idx == total_idx: continue

                matches = 0
                total_rows = 0
                for _, row in df.iterrows():
                    try:
                        qty = Decimal(str(row.iloc[qty_idx])).replace(",", ".")
                        # basic float fix for qty
                        qty = Decimal(str(row.iloc[qty_idx]).replace(",", "."))
                        unit = parse_brl(row.iloc[unit_idx])
                        total = parse_brl(row.iloc[total_idx])

                        if unit and total and qty:
                            if (qty * unit).quantize(Decimal('0.01'), ROUND_HALF_UP) == total.quantize(Decimal('0.01'), ROUND_HALF_UP):
                                matches += 1
                        total_rows += 1
                    except:
                        continue

                if total_rows > 0 and (matches / total_rows) > 0.7:
                    return {"unit_price": unit_idx, "total_price": total_idx}

        return {}

    def extract_from_pdf(self, path: Path) -> List[Dict]:
        items = []
        try:
            with pymupdf.open(path) as doc:
                for page in doc:
                    tabs = page.find_tables()
                    for tab in tabs:
                        df = tab.to_pandas()
                        header_idx = self._identify_header_row(df)
                        if header_idx is None: continue

                        df.columns = df.iloc[header_idx]
                        df = df.iloc[header_idx + 1:].reset_index(drop=True)

                        # Mapping roles
                        role_map = {}
                        for idx, col_name in enumerate(df.columns):
                            role = identify_column_role(str(col_name))
                            if role: role_map[role] = idx

                        # Fix for missing indices
                        qty_idx = role_map.get("quantity", 3 if len(df.columns) > 3 else 0)

                        # Math inference for prices
                        prices = self._infer_monetary_columns(df, qty_idx)
                        unit_idx = prices.get("unit_price", role_map.get("unit_price", 4 if len(df.columns) > 4 else -1))
                        total_idx = prices.get("total_price", role_map.get("total_price", 5 if len(df.columns) > 5 else -1))

                        for _, row in df.iterrows():
                            cols = row.values
                            if len(cols) < 1 or pd.isna(cols[0]): continue

                            # Extraction with safety
                            item_id = str(cols[0])
                            desc = str(cols[1]) if len(cols) > 1 else ""
                            unit = str(cols[2]) if len(cols) > 2 else ""

                            try:
                                qty_val = str(cols[qty_idx]).replace(",", ".") if len(cols) > qty_idx else "0"
                                qty = Decimal(qty_val)
                            except:
                                qty = Decimal("0")

                            unit_price = parse_brl(cols[unit_idx]) if unit_idx != -1 and len(cols) > unit_idx else None
                            total_price = parse_brl(cols[total_idx]) if total_idx != -1 and len(cols) > total_idx else None

                            items.append({
                                "id": item_id,
                                "description": desc,
                                "unit": unit,
                                "quantity": qty,
                                "unit_price": unit_price,
                                "total_price": total_price,
                                "ceiling_price": unit_price # Compatibility with old code
                            })
        except Exception as e:
            print(f"Erro ao ler PDF {path}: {e}")
        return items

    def extract_from_xlsx(self, path: Path) -> List[Dict]:
        items = []
        try:
            all_sheets = pd.read_excel(path, sheet_name=None)
            for sheet_name, df in all_sheets.items():
                header_idx = self._identify_header_row(df)
                if header_idx is None: continue

                df.columns = df.iloc[header_idx]
                df = df.iloc[header_idx + 1:].reset_index(drop=True)

                role_map = {}
                for idx, col_name in enumerate(df.columns):
                    role = identify_column_role(str(col_name))
                    if role: role_map[role] = idx

                qty_idx = role_map.get("quantity", 3 if len(df.columns) > 3 else 0)
                prices = self._infer_monetary_columns(df, qty_idx)
                unit_idx = prices.get("unit_price", role_map.get("unit_price", 4 if len(df.columns) > 4 else -1))
                total_idx = prices.get("total_price", role_map.get("total_price", 5 if len(df.columns) > 5 else -1))

                for _, row in df.iterrows():
                    cols = row.values
                    if len(cols) < 1 or pd.isna(cols[0]): continue

                    try:
                        qty_val = str(cols[qty_idx]).replace(",", ".") if len(cols) > qty_idx else "0"
                        qty = Decimal(qty_val)
                    except:
                        qty = Decimal("0")

                    unit_price = parse_brl(cols[unit_idx]) if unit_idx != -1 and len(cols) > unit_idx else None
                    total_price = parse_brl(cols[total_idx]) if total_idx != -1 and len(cols) > total_idx else None

                    items.append({
                        "id": str(cols[0]),
                        "description": str(cols[1]) if len(cols) > 1 else "",
                        "unit": str(cols[2]) if len(cols) > 2 else "",
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total_price": total_price,
                        "ceiling_price": unit_price
                    })
        except Exception as e:
            print(f"Erro ao ler XLSX {path}: {e}")
        return items

    def extract_from_md(self, path: Path) -> List[Dict]:
        # Implementation simplified for brevity, would follow the same logic as above
        # but for markdown tables
        return []

    def extract_from_docx(self, path: Path) -> List[Dict]:
        # Implementation simplified for brevity, would follow the same logic as above
        # but for docx tables
        return []

    def parse(self, path: Path) -> List[Dict]:
        suffix = path.suffix.lower()
        if suffix == ".pdf": return self.extract_from_pdf(path)
        if suffix == ".md": return self.extract_from_md(path)
        if suffix == ".docx": return self.extract_from_docx(path)
        if suffix in [".xlsx", ".xls"]: return self.extract_from_xlsx(path)
        return []
