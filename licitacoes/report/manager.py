from typing import List, Dict, Any
from pathlib import Path
from licitacoes.rules.pipeline import FullParticipantChecker
from licitacoes.report.findings_xlsx import findings_report_gen
from licitacoes.report.minutas import draft_gen

class AnalysisManager:
    """Orchestrates the analysis of multiple participants and report generation."""

    def __init__(self, edital_json_path: Path):
        import json
        with open(edital_json_path, "r", encoding="utf-8") as f:
            self.edital_data = json.load(f)
        self.pipeline = FullParticipantChecker(self.edital_data)

    def run_all(self, participants_root: Path, output_dir: Path):
        all_results = {}

        # 1. Process each participant folder
        for bidder_folder in participants_root.iterdir():
            if bidder_folder.is_dir():
                print(f"Analisando {bidder_folder.name}...")
                findings = self.pipeline.check_folder(bidder_folder)
                all_results[bidder_folder.name] = findings

        # 2. Generate Excel Report
        report_path = output_dir / "relatorio_achados.xlsx"
        findings_report_gen.generate(all_results, report_path)
        print(f"Relatório de achados gerado: {report_path}")

        # 3. Generate Drafts for critical cases
        drafts_dir = output_dir / "minutas"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        for bidder, findings in all_results.items():
            if any(f.severity in ["critical", "high"] for f in findings):
                draft = draft_gen.generate_recurso(bidder, findings, self.edital_data)
                with open(drafts_dir / f"recurso_{bidder}.txt", "w", encoding="utf-8") as f:
                    f.write(draft)
                print(f"Minuta de recurso gerada para {bidder}")

        return all_results

# Singleton helper
manager = None
