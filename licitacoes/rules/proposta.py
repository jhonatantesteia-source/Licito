from typing import List
from licitacoes.rules.base import BaseRule, RuleResult, Finding

class ProposalArithmeticRule(BaseRule):
    """Checks for arithmetic errors and ceiling price violations."""

    def evaluate(self, context: dict) -> RuleResult:
        """
        Context expected: {
            'items': [
                {'id': '1', 'qty': 10, 'unit_price': 100.0, 'total': 1000.0, 'ceiling': 110.0, 'file': '...', 'page': ...},
                ...
            ],
            'global_total': 5000.0
        }
        """
        items = context.get('items', [])
        global_total = context.get('global_total', 0.0)
        findings = []
        calculated_global_total = 0.0

        for item in items:
            qty = item.get('qty', 0)
            unit = item.get('unit_price', 0.0)
            total = item.get('total', 0.0)
            ceiling = item.get('ceiling', float('inf'))

            # 1. Check Arithmetic (Qty * Unit == Total)
            # Using small epsilon for float precision
            if abs((qty * unit) - total) > 0.01:
                findings.append(Finding(
                    document="Proposta",
                    finding_text=f"Erro aritmético no item {item['id']}: {qty} x {unit} != {total}.",
                    severity="medium",
                    rule_violated="Exatidão aritmética da proposta",
                    evidence=f"Qtde: {qty}, Unit: {unit}, Total: {total}",
                    file_path=item.get('file', 'Unknown'),
                    page=item.get('page'),
                    suggested_action="Solicitar correção ou desclassificar item."
                ))

            # 2. Check Ceiling Price (Unit <= Ceiling)
            if unit > ceiling:
                findings.append(Finding(
                    document="Proposta",
                    finding_text=f"Preço unitário do item {item['id']} acima do teto ({unit} > {ceiling}).",
                    severity="critical",
                    rule_violated="Limite de preço máximo do edital",
                    evidence=f"Unitário: {unit}, Teto: {ceiling}",
                    file_path=item.get('file', 'Unknown'),
                    page=item.get('page'),
                    suggested_action="Desclassificação imediata do item."
                ))

            calculated_global_total += total

        # 3. Check Global Total
        if abs(calculated_global_total - global_total) > 0.01:
            findings.append(Finding(
                document="Proposta",
                finding_text=f"Soma dos itens ({calculated_global_total}) difere do total global informado ({global_total}).",
                severity="medium",
                rule_violated="Consistência do total da proposta",
                    evidence=f"Soma: {calculated_global_total}, Total Inf: {global_total}",
                file_path="proposta.pdf",
                page=None,
                suggested_action="Solicitar esclarecimento."
            ))

        return RuleResult(
            passed=len(findings) == 0,
            findings=findings
        )
