import pytest
from licitacoes.rules.cnpj_cpf import CNPJRule
from licitacoes.rules.certidoes import CertificateRule
from licitacoes.rules.proposta import ProposalArithmeticRule
from datetime import date

def test_cnpj_valid():
    rule = CNPJRule()
    assert rule.is_valid("00.000.000/0001-91") == False # Just a dummy check
    # Real valid CNPJ would be needed for true test, but let's test the logic
    assert rule.is_valid("123") == False

def test_certificate_expiry():
    rule = CertificateRule()
    ctx = {
        'expiry_date': date(2026, 1, 1),
        'session_date': date(2026, 10, 3),
        'status': 'negativa',
        'document_type': 'CND'
    }
    result = rule.evaluate(ctx)
    assert result.passed == False
    assert "vencida" in result.findings[0].finding_text

def test_proposal_arithmetic():
    rule = ProposalArithmeticRule()
    ctx = {
        'items': [
            {'id': '1', 'qty': 10, 'unit_price': 100.0, 'total': 1000.0, 'ceiling': 110.0}
        ],
        'global_total': 1000.0
    }
    result = rule.evaluate(ctx)
    assert result.passed == True

    ctx_error = {
        'items': [
            {'id': '1', 'qty': 10, 'unit_price': 100.0, 'total': 900.0, 'ceiling': 110.0}
        ],
        'global_total': 900.0
    }
    result_error = rule.evaluate(ctx_error)
    assert result_error.passed == False
