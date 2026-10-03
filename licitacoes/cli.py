import typer
from pathlib import Path
from datetime import date
from licitacoes.ingest.document_loader import DocumentIngestor
from licitacoes.edital.extractor import EditalExtractor
from licitacoes.report.xlsx import proposal_gen
from licitacoes.config import settings

app = typer.Typer()

@app.command()
def analisar_edital(arquivo: Path):
    """Lê e analisa um edital para extrair informações estruturadas."""
    print(f"Analisando arquivo: {arquivo}...")

    # 1. Ingestão
    ingestor = DocumentIngestor()
    text = ingestor.extract_text(arquivo)

    # 2. Extração com LLM
    extractor = EditalExtractor()
    edital_data = extractor.extract(text, str(arquivo))

    if edital_data:
        # Save to JSON
        output_path = Path(settings.paths.output_dir) / "edital.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(edital_data.model_dump_json(indent=2))

        print(f"Análise concluída. Dados salvos em: {output_path}")
        print(f"Órgão: {edital_data.organ}")
        print(f"Objeto: {edital_data.object}")
    else:
        print("Falha ao extrair dados do edital.")

@app.command()
def gerar_proposta(edital_json: Path):
    """Gera a planilha de proposta baseada no arquivo edital.json."""
    import json
    from licitacoes.edital.schema import EditalSchema

    print(f"Lendo edital: {edital_json}...")
    with open(edital_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        edital = EditalSchema(**data)

    output_path = Path(settings.paths.output_dir) / "proposta.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_gen.generate(edital, output_path)

    print(f"Proposta gerada com sucesso em: {output_path}")

@app.command()
def conferir_participante(pasta_licitante: Path, edital_json: Path):
    """Confere a habilitação de um participante contra as regras do edital."""
    import json
    from licitacoes.rules.pipeline import FullParticipantChecker

    print(f"Analisando documentos do licitante em: {pasta_licitante}...")

    with open(edital_json, "r", encoding="utf-8") as f:
        edital_data = json.load(f)

    pipeline = FullParticipantChecker(edital_data)
    findings = pipeline.check_folder(pasta_licitante)

    if not findings:
        print("Nenhuma irregularidade encontrada.")
    else:
        print(f"\nForam encontrados {len(findings)} achados:\n")
        for f in findings:
            print(f"[{f.severity.upper()}] {f.document}: {f.finding_text}")
            print(f"  Evidência: {f.evidence}")
            print(f"  Ação Sugerida: {f.suggested_action}")
            print("-" * 40)

@app.command()
def analisar_todos(pasta_licitantes: Path, edital_json: Path):
    """Analisa todos os participantes de uma vez e gera relatórios consolidados."""
    from licitacoes.report.manager import AnalysisManager
    from licitacoes.config import settings

    print(f"Iniciando análise em massa de: {pasta_licitantes}...")

    output_dir = Path(settings.paths.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manager = AnalysisManager(edital_json)
    manager.run_all(pasta_licitantes, output_dir)

    print("\nProcesso concluído com sucesso.")

if __name__ == "__main__":
    app()
