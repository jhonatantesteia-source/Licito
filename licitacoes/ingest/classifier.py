from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from licitacoes.llm.client import llm_client

class DocumentClass(BaseModel):
    """Classification of a document type."""
    category: str = Field(..., description="Category (e.g., 'contrato_social', 'cnd_federal', 'proposta', 'balanco', 'atestado_tecnico')")
    confidence: float = Field(..., description="Confidence score 0-1")
    reason: str = Field(..., description="Reason for this classification")

class ExtractedDocumentData(BaseModel):
    """Generic container for data extracted from a document."""
    category: str
    fields: Dict[str, Any]
    source_snippets: List[str]

class DocumentClassifier:
    """Uses LLM to classify documents based on their content."""

    def classify(self, text: str, filename: str) -> DocumentClass:
        prompt = f"""
Você é um especialista em análise de documentos de licitações públicas brasileiras.
Analise o conteúdo do arquivo '{filename}' e classifique-o em uma das seguintes categorias:
- 'contrato_social': Contratos sociais, estatutos, alterações contratuais.
- 'cnd_federal': Certidão Negativa de Débitos Relativos a Créditos da União (CND).
- 'cnd_estadual': Certidões de tributos estaduais.
- 'cnd_municipal': Certidões de tributos municipais.
- 'crf_fgts': Certificado de Regularidade do FGTS.
- 'cndt': Certidão Negativa de Débitos Trabalhistas.
- 'balanco': Balanço Patrimonial, DRE.
- 'atestado_tecnico': Atestados de capacidade técnica.
- 'proposta': Proposta de preços, planilha orçamentária.
- 'declaracao': Declarações diversas exigidas em edital.
- 'outros': Documentos que não se encaixam nas categorias acima.

Texto do documento:
---
{text[:4000]}
---

Retorne APENAS um JSON seguindo o esquema:
{{
  "category": "categoria_escolhida",
  "confidence": 0.95,
  "reason": "Explicação curta do porquê"
}}
"""
        result = llm_client.generate_structured(prompt, DocumentClass)
        return result or DocumentClass(category="outros", confidence=0.0, reason="Falha na extração")

# Singleton
classifier = DocumentClassifier()
