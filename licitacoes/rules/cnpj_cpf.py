import re
from typing import Optional
from licitacoes.rules.base import BaseRule, RuleResult, Finding

class CNPJRule(BaseRule):
    """Validates the CNPJ check digit."""

    def _calculate_digit(self, digits: list[int], weight: list[int]) -> int:
        sum_val = sum(d * w for d, w in zip(digits, weight))
        remainder = sum_val % 11
        return 0 if remainder == 0 else 11 - remainder

    def is_valid(self, cnpj: str) -> bool:
        # Clean string
        cnpj = re.sub(r'\D', '', cnpj)
        if len(cnpj) != 14:
            return False

        digits = [int(d) for d in cnpj]

        # First digit
        w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if self._calculate_digit(digits[:12], w1) != digits[12]:
            return False

        # Second digit
        w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if self._calculate_digit(digits[:13], w2) != digits[13]:
            return False

        return True

    def evaluate(self, context: dict) -> RuleResult:
        """
        Context expected: {'cnpj': '...', 'document': '...', 'file': '...', 'page': ...}
        """
        cnpj = context.get('cnpj')
        if not cnpj:
            return RuleResult(passed=True) # Not applicable

        valid = self.is_valid(cnpj)
        if not valid:
            return RuleResult(
                passed=False,
                findings=[Finding(
                    document=context.get('document', 'Unknown'),
                    finding_text="CNPJ com dígito verificador inválido.",
                    severity="critical",
                    rule_violated="Regra Determinística de Validação de CNPJ",
                    evidence=cnpj,
                    file_path=context.get('file', 'Unknown'),
                    page=context.get('page'),
                    suggested_action="Inabilitação imediata por documento inválido."
                )]
            )
        return RuleResult(passed=True)
