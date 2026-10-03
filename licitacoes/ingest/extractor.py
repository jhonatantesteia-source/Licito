from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from licitacoes.llm.client import llm_client

class FieldExtraction(BaseModel):
    value: Any
    source: str

class DocumentFields(BaseModel):
    fields: Dict[str, FieldExtraction]

class DataExtractor:
    """Extracts specific fields from documents based on their category."""

    def extract_fields(self, text: str, category: str, filename: str) -> Dict[str, Any]:
        # Define schemas for different document types
        schemas = {
            "cnd_federal": {
                "cnpj": "CNPJ da empresa",
                "issue_date": "Data de emissão (YYYY-MM-DD)",
                "expiry_date": "Data de validade (YYYY-MM-DD)",
                "status": "Situação (Negativa, Positiva com efeito de negativa, etc)",
                "control_number": "Número de controle/autenticação"
            },
            "crf_fgts": {
                "cnpj": "CNPJ da empresa",
                "expiry_date": "Data de validade (YYYY-MM-DD)",
                "status": "Situação"
            },
            "contrato_social": {
                "razao_social": "Razão Social",
                "cnpj": "CNPJ",
                "social_object": "Objeto Social (atividade da empresa)",
                "last_update": "Data da última alteração"
            },
            "proposta": {
                "global_total": "Valor Total Global",
                "validity": "Validade da proposta",
                "items": "Lista de itens com: ID, Descrição, Qtde, Unitário, Total"
            }
        }

        schema = schemas.get(category)
        if not schema:
            return {}

        prompt = f"""
Extraia as seguintes informações do documento classificado como '{category}'.
Sempre retorne o valor e o trecho literal do texto onde a informação foi encontrada.

Campos para extrair:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Texto do documento:
---
{text[:6000]}
---

Retorne APENAS um JSON no formato:
{{
  "fields": {{
    "campo1": {{ "value": "valor", "source": "trecho literal" }},
    "campo2": {{ "value": "valor", "source": "trecho literal" }}
  }}
}}
"""
        # We'll use a simpler Pydantic model for the raw response since the values vary
        # But we can validate the keys
        try:
            # Using a generic Dict response for flexibility in field types
            result = llm_client.generate_structured(prompt, DocumentFields)
            if result:
                # Flatten to simple value for the rules engine
                return {k: v.value for k, v in result.fields.items()}
        except Exception as e:
            print(f"Error extracting fields for {category}: {e}")

        return {}

import json # Added missing import
# Singleton
data_extractor = DataExtractor()
