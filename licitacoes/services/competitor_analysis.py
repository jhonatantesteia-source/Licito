from pathlib import Path
import streamlit as st
from licitacoes.services import persistence as db
from licitacoes.edital.deterministic_parser import DeterministicParser
from licitacoes.services.money import parse_brl_to_cents

class CompetitorAnalysisService:
    """
    Serviço responsável por analisar arquivos de concorrentes,
    extraindo preços e verificando documentação.
    """

    @staticmethod
    def analyze_competitor(competitor_id: int, tender_id: int):
        """
        Analisa os arquivos do concorrente e salva os preços no banco.
        Retorna uma lista de achados (irregularidades).
        """
        # 1. Buscar arquivos do concorrente
        files = db.get_competitor_files(competitor_id)
        if not files:
            return [{"type": "warning", "msg": "Nenhum arquivo enviado para análise."}]

        # 2. Identificar qual arquivo é a proposta
        # Prioridade: arquivos com 'proposta', 'planilha', 'precos' no nome
        proposal_file_path = None
        keywords = ["proposta", "planilha", "preco", "valor", "orcamento"]

        for f in files:
            if any(kw in f["file_name"].lower() for kw in keywords):
                proposal_file_path = f["file_path"]
                break

        # Se não achou por nome, tenta o primeiro arquivo disponível
        if not proposal_file_path:
            proposal_file_path = files[0]["file_path"]

        # 3. Extração de Preços
        achados = []
        try:
            parser = DeterministicParser()
            items_extracted = parser.parse(Path(proposal_file_path))

            if items_extracted:
                # Salvar preços no banco
                rows = []
                for it in items_extracted:
                    # O parser retorna 'ceiling_price' para o valor extraído
                    rows.append((it["number"] if "number" in it else it["id"], it["ceiling_price"], it.get("brand", "")))

                db.save_competitor_proposal(competitor_id, rows)

                # Verificar se algum preço está acima do teto do edital
                tender_items = db.get_items(tender_id)
                ceiling_map = {i["number"]: i["ceiling_cents"] for i in tender_items}

                for it in items_extracted:
                    item_id = it["number"] if "number" in it else it["id"]
                    # Tentar converter id para int para bater com o map
                    try:
                        item_id_int = int(float(item_id))
                    except:
                        continue

                    ceiling = ceiling_map.get(item_id_int)
                    if ceiling and it["ceiling_price"] > ceiling:
                        achados.append({
                            "type": "error",
                            "msg": f"Preço acima do teto no Item {item_id_int}: {format_brl(it['ceiling_price'])} > {format_brl(ceiling)}"
                        })
            else:
                achados.append({"type": "warning", "msg": f"Não foi possível extrair preços do arquivo: {Path(proposal_file_path).name}"})

        except Exception as e:
            achados.append({"type": "error", "msg": f"Erro ao processar proposta: {str(e)}"})

        # 4. Verificação Documental (Simulada baseada em nomes de arquivos)
        required_docs = ["Certidão FGTS", "Certidão Negativa", "Atestado Técnico"]
        found_files = [f["file_name"].lower() for f in files]

        for req in required_docs:
            if not any(req.lower() in fn for fn in found_files):
                achados.append({
                    "type": "error",
                    "msg": f"Documento obrigatório ausente: {req}"
                })

        return achados
