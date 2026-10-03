import json
from pathlib import Path
from datetime import date
from licitacoes.ingest.document_loader import DocumentIngestor
from licitacoes.ingest.classifier import classifier
from licitacoes.ingest.extractor import data_extractor
from licitacoes.rules.habilitacao import checker
from licitacoes.rules.semantic import semantic_rule
from licitacoes.rules.base import Finding

class FullParticipantChecker:
    """Full pipeline: PDF -> Text -> Classify -> Extract -> Deterministic Rules -> Semantic Rules."""

    def __init__(self, edital_data: dict):
        self.edital_data = edital_data
        self.ingestor = DocumentIngestor()

    def check_folder(self, folder_path: Path) -> List[Finding]:
        all_findings = []
        participant_structured_data = {
            "certificates": [],
            "proposal_items": [],
            "social_object": None
        }

        # Process all files in folder
        for file_path in folder_path.iterdir():
            if file_path.suffix.lower() not in [".pdf", ".docx", ".txt"]:
                continue

            text = self.ingestor.extract_text(file_path)
            doc_class = classifier.classify(text, file_path.name)

            # Extract data based on classification
            fields = data_extractor.extract_fields(text, doc_class.category, file_path.name)

            if doc_class.category == "contrato_social":
                participant_structured_data["social_object"] = fields.get("social_object")
                participant_structured_data["cnpj"] = fields.get("cnpj")
                participant_structured_data["cnpj_file"] = file_path.name

            elif doc_class.category in ["cnd_federal", "crf_fgts", "cndt", "cnd_estadual", "cnd_municipal"]:
                participant_structured_data["certificates"].append({
                    "document_type": doc_class.category,
                    "expiry_date": fields.get("expiry_date"), # Expected YYYY-MM-DD
                    "status": fields.get("status"),
                    "file": file_path.name,
                    "page": 1
                })

            elif doc_class.category == "proposta":
                # For simplicity in Phase 3, we'll simulate the extracted items list
                # In a full version, the extractor would return a list of objects
                participant_structured_data["proposal_items"] = [] # Simplified
                participant_structured_data["proposal_total"] = fields.get("global_total")

        # 1. Run Deterministic Rules
        # We need to convert date strings to date objects for the rules engine
        # This is a simplification for the demo
        deterministic_findings = checker.check(participant_structured_data)
        all_findings.extend(deterministic_findings)

        # 2. Run Semantic Rules
        if participant_structured_data["social_object"] and self.edital_data.get("object"):
            comp = semantic_rule.check_social_object_compatibility(
                participant_structured_data["social_object"],
                self.edital_data["object"]
            )
            if not comp.is_compatible:
                all_findings.append(Finding(
                    document="Contrato Social",
                    finding_text="Objeto social incompatível com o objeto da licitação.",
                    severity="medium",
                    rule_violated="Compatibilidade de atividade econômica",
                    evidence=comp.evidence,
                    file_path="contrato_social.pdf",
                    suggested_action="Analisar se a empresa pode executar o serviço."
                ))

        return all_findings

# Singleton (initialized per edital)
full_checker = None
