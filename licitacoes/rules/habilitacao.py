from pathlib import Path
from typing import List, Dict, Any
from licitacoes.rules.cnpj_cpf import CNPJRule
from licitacoes.rules.certidoes import CertificateRule
from licitacoes.rules.proposta import ProposalArithmeticRule
from licitacoes.rules.base import Finding

class ParticipantChecker:
    """Engine that runs all deterministic rules against a participant's folder."""

    def __init__(self):
        self.rules = {
            "cnpj": CNPJRule(),
            "certificates": CertificateRule(),
            "proposal": ProposalArithmeticRule()
        }

    def check(self, participant_data: Dict[str, Any]) -> List[Finding]:
        all_findings = []

        # 1. Check CNPJ
        cnpj_ctx = {
            'cnpj': participant_data.get('cnpj'),
            'document': 'Cartão CNPJ',
            'file': participant_data.get('cnpj_file', 'unknown'),
            'page': 1
        }
        res = self.rules["cnpj"].evaluate(cnpj_ctx)
        all_findings.extend(res.findings)

        # 2. Check Certificates (Assuming a list of extracted certs)
        certs = participant_data.get('certificates', [])
        for cert in certs:
            cert_ctx = {
                **cert,
                'session_date': participant_data.get('session_date'),
                'file': cert.get('file', 'unknown'),
                'page': cert.get('page', 1)
            }
            res = self.rules["certificates"].evaluate(cert_ctx)
            all_findings.extend(res.findings)

        # 3. Check Proposal
        prop_ctx = {
            'items': participant_data.get('proposal_items', []),
            'global_total': participant_data.get('proposal_total', 0.0)
        }
        res = self.rules["proposal"].evaluate(prop_ctx)
        all_findings.extend(res.findings)

        return all_findings

# Singleton
checker = ParticipantChecker()
