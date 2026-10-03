from typing import List, Any
from pydantic import BaseModel
from licitacoes.llm.client import llm_client

class CompatibilityResult(BaseModel):
    is_compatible: bool
    reason: str
    evidence: str

class SemanticRule:
    """Rules that require semantic understanding via LLM."""

    def check_social_object_compatibility(self, social_object: str, tender_object: str) -> CompatibilityResult:
        prompt = f"""
Analise se o Objeto Social de uma empresa é compatível com o Objeto de uma Licitação.

Objeto Social da Empresa:
---
{social_object}
---

Objeto da Licitação:
---
{tender_object}
---

Regra: A empresa deve possuir atividade econômica (CNAE ou descrição) que permita a execução do objeto da licitação.

Retorne APENAS um JSON:
{{
  "is_compatible": true/false,
  "reason": "Explicação detalhada da compatibilidade ou incompatibilidade",
  "evidence": "Trecho do objeto social que justifica a decisão"
}}
"""
        result = llm_client.generate_structured(prompt, CompatibilityResult)
        return result or CompatibilityResult(is_compatible=False, reason="Falha na análise", evidence="")

# Singleton
semantic_rule = SemanticRule()
