from typing import List, Dict, Any
from pathlib import Path
from licitacoes.rules.base import Finding

class DraftGenerator:
    """Generates legal drafts for appeals, challenges, or clarification requests."""

    def generate_recurso(self, bidder: str, findings: List[Finding], edital_data: dict) -> str:
        # Filter for high/critical findings
        relevant = [f for f in findings if f.severity in ["critical", "high"]]
        if not relevant:
            return "Não foram encontrados achados graves o suficiente para fundamentar um recurso."

        draft = f"À Comissão de Contratação / Pregoeiro\n"
        draft += f"Referência: {edital_data.get('process_number', 'Processo nº Não Informado')}\n"
        draft += f"Objeto: {edital_data.get('object', 'Objeto não informado')}\n\n"
        draft += f"Prezados,\n\n"
        draft += f"Na qualidade de licitante interessado, vimos por meio deste solicitar a análise de irregularidade na documentação apresentada pela empresa {bidder}.\n\n"

        for i, f in enumerate(relevant, 1):
            draft += f"{i}. {f.document} - {f.finding_text}\n"
            draft += f"   Fundamentação: {f.rule_violated}\n"
            draft += f"   Evidência: \"{f.evidence}\" (Arquivo: {f.file_path}, Pág: {f.page or 'N/A'})\n"
            draft += f"   Base Legal: Conforme a Lei 14.133/2021, a ausência ou irregularidade deste documento enseja a inabilitação do licitante.\n\n"

        draft += "Diante do exposto, requer-se a inabilitação da referida empresa ou a realização de diligência para comprovação da regularidade.\n\n"
        draft += "Atenciosamente,\n\n"
        draft += "[Nome da sua Empresa]\n"
        draft += "[CNPJ]\n\n"
        draft += "⚠️ AVISO: Este documento é um RASCUNHO gerado automaticamente e deve ser revisado por um advogado antes do envio."

        return draft

# Singleton
draft_gen = DraftGenerator()
