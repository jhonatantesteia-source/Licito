from datetime import datetime, date
from typing import Optional, Dict
from licitacoes.rules.base import BaseRule, RuleResult, Finding

class CertificateRule(BaseRule):
    """Validates expiration and status of certificates."""

    def evaluate(self, context: dict) -> RuleResult:
        """
        Context expected: {
            'document_type': '...',
            'issue_date': date,
            'expiry_date': date,
            'status': 'negativa/positiva',
            'session_date': date,
            'file': '...',
            'page': ...
        }
        """
        expiry = context.get('expiry_date')
        session_date = context.get('session_date')
        status = context.get('status', '').lower()
        doc_type = context.get('document_type', 'Certidão')

        if not expiry or not session_date:
            return RuleResult(passed=True) # Not enough data for this rule

        # 1. Check Expiration
        if expiry < session_date:
            return RuleResult(
                passed=False,
                findings=[Finding(
                    document=doc_type,
                    finding_text=f"Certidão vencida na data da sessão ({expiry} < {session_date}).",
                    severity="high",
                    rule_violated="Exigência de validade do edital",
                    evidence=f"Validade: {expiry}",
                    file_path=context.get('file', 'Unknown'),
                    page=context.get('page'),
                    suggested_action="Pedir diligência para atualização ou inabilitar."
                )]
            )

        # 2. Check Positive Status
        if "positiva" in status and "efeitos de negativa" not in status:
            return RuleResult(
                passed=False,
                findings=[Finding(
                    document=doc_type,
                    finding_text="Certidão apresenta situação POSITIVA (não aceitável).",
                    severity="critical",
                    rule_violated="Exigência de regularidade fiscal",
                    evidence=f"Status: {status}",
                    file_path=context.get('file', 'Unknown'),
                    page=context.get('page'),
                    suggested_action="Inabilitação por irregularidade fiscal."
                )]
            )

        return RuleResult(passed=True)
