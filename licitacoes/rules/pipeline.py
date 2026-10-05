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
                # Use DeterministicParser to extract structured proposal items
                from licitacoes.edital.deterministic_parser import DeterministicParser
                parser = DeterministicParser()
                deterministic_items = parser.parse(file_path)

                # LLM extraction (already done via fields = data_extractor.extract_fields)
                # We need to merge them ensuring deterministic precedence.

                merged_items = []
                conflicts = []

                # deterministic_items is a list of dicts from DeterministicParser
                # Fields: id, description, unit, quantity, unit_price, total_price, ceiling_price

                # The LLM extracted items might be in fields.get("proposal_items")
                llm_items = fields.get("proposal_items", [])
                if isinstance(llm_items, str):
                    # Try to parse if it's a JSON string
                    import json
                    try:
                        llm_items = json.loads(llm_items)
                    except:
                        llm_items = []

                # Create a map for LLM items for easier lookup
                llm_map = {str(item.get("id")): item for item in llm_items if item.get("id")}

                for d_item in deterministic_items:
                    item_id = str(d_item["id"])
                    l_item = llm_map.get(item_id, {})

                    merged_item = d_item.copy()

                    # Check for conflicts and ensure precedence
                    for field in ["unit_price", "total_price", "quantity"]:
                        d_val = d_item.get(field)
                        l_val = l_item.get(field)

                        if d_val is not None:
                            # Deterministic wins. Check for conflict.
                            if l_val is not None and l_val != d_val:
                                conflicts.append({
                                    "item_id": item_id,
                                    "field": field,
                                    "deterministic": d_val,
                                    "llm": l_val,
                                    "action": "kept_deterministic"
                                })
                        else:
                            # LLM is fallback
                            merged_item[field] = l_val

                    merged_items.append(merged_item)

                # Handle items only found by LLM
                deterministic_ids = {str(i["id"]) for i in deterministic_items}
                for l_item in llm_items:
                    l_id = str(l_item.get("id"))
                    if l_id and l_id not in deterministic_ids:
                        merged_items.append(l_item)

                participant_structured_data["proposal_items"] = merged_items
                participant_structured_data["proposal_total_declared"] = fields.get("global_total")
                participant_structured_data["extraction_conflicts"] = conflicts

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
