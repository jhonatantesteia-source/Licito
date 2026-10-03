from typing import Optional
from pathlib import Path
from datetime import date
from licitacoes.edital.schema import EditalSchema
from licitacoes.llm.client import llm_client

class EditalExtractor:
    """Orchestrates the extraction of information from edital text."""

    def extract(self, text: str, filename: str) -> Optional[EditalSchema]:
        # In a real scenario, we might split the text into chunks if it's too long.
        # For Phase 1, we'll use a single comprehensive prompt.

        prompt = f"""
Você é um especialista em licitações públicas brasileiras (Lei 14.133/2021).
Sua tarefa é extrair informações estruturadas do seguinte edital.

Regras rigorosas:
1. Retorne APENAS um JSON válido.
2. Se não encontrar a informação, use null ou lista vazia.
3. Para cada campo, inclua o trecho literal do texto como 'source'.
4. Datas devem estar no formato YYYY-MM-DD.

Texto do Edital:
---
{text}
---

JSON Schema esperado:
{{
  "organ": "Nome do Órgão",
  "modality": "Modalidade",
  "process_number": "Número do Processo",
  "object": "Descrição do Objeto",
  "judgment_criterion": "Critério de Julgamento",
  "deadlines": [
    {{ "event": "Nome do Evento", "date": "YYYY-MM-DD", "description": "Detalhes", "source": {{ "text": "...", "page": 1, "file": "{filename}" }} }}
  ],
  "me_epp_exclusive": true/false,
  "simples_nacional_required": true/false,
  "restrictions": ["Restrição 1", "Restrição 2"],
  "required_documents": [
    {{ "name": "Nome do Doc", "legal_basis": "Lei X", "validity_days": 90, "required_for_all": true, "source": {{ "text": "...", "page": 1, "file": "{filename}" }} }}
  ],
  "items": [
    {{ "id": "1", "description": "Desc", "unit": "Un", "quantity": 10, "ceiling_price": 100.0, "brand_required": "Marca X", "source": {{ "text": "...", "page": 1, "file": "{filename}" }} }}
  ],
  "payment_terms": "Termos de pagamento",
  "penalties": "Penalidades",
  "source_file": "{filename}",
  "extraction_date": "{date.today().isoformat()}"
}}
"""
        return llm_client.generate_structured(prompt, EditalSchema)

# Singleton
extractor = EditalExtractor()
