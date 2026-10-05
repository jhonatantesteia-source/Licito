from typing import List
from decimal import Decimal, ROUND_HALF_UP
from licitacoes.rules.base import BaseRule, RuleResult, Finding

class ProposalArithmeticRule(BaseRule):
    """Checks for arithmetic errors and ceiling price violations using Decimal precision."""

    def evaluate(self, context: dict) -> RuleResult:
        """
        Context expected: {
            'items': [
                {'id': '1', 'qty': Decimal('10'), 'unit_price': Decimal('100.00'), 'total': Decimal('1000.00'), 'ceiling': Decimal('110.00'), 'file': '...', 'page': ...},
                ...
            ],
            'proposal_total_declared': Decimal('5000.00')
        }
        """
        items = context.get('items', [])
        # Convert global_total to Decimal if it's not already
        try:
            global_total_declared = Decimal(str(context.get('proposal_total_declared', '0'))).quantize(Decimal('0.01'), ROUND_HALF_UP)
        except:
            global_total_declared = Decimal('0.00')

        findings = []
        calculated_global_total = Decimal('0.00')

        for item in items:
            # Ensure all values are Decimals
            try:
                qty = Decimal(str(item.get('qty', '0'))).quantize(Decimal('0.01'), ROUND_HALF_UP)
                unit = Decimal(str(item.get('unit_price', '0'))).quantize(Decimal('0.01'), ROUND_HALF_UP)
                total = Decimal(str(item.get('total', '0'))).quantize(Decimal('0.01'), ROUND_HALF_UP)
                ceiling = Decimal(str(item.get('ceiling', '999999999.99'))).quantize(Decimal('0.01'), ROUND_HALF_UP)
            except:
                continue

            # 1. Check Arithmetic (Qty * Unit == Total)
            expected_total = (qty * unit).quantize(Decimal('0.01'), ROUND_HALF_UP)
            if expected_total != total:
                findings.append(Finding(
                    document="Proposta",
                    finding_text=f"Erro aritmético no item {item['id']}: {qty} x {unit} != {total}.",
                    severity="medium",
                    rule_violated="Exatidão aritmética da proposta",
                    evidence=f"Qtde: {qty}, Unit: {unit}, Total: {total} (Esperado: {expected_total})",
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
        if calculated_global_total != global_total_declared:
            findings.append(Finding(
                document="Proposta",
                finding_text=f"Soma dos itens ({calculated_global_total}) difere do total global informado ({global_total_declared}).",
                severity="medium",
                rule_violated="Consistência do total da proposta",
                evidence=f"Soma: {calculated_global_total}, Total Inf: {global_total_declared}",
                file_path="proposta.pdf",
                page=None,
                suggested_action="Solicitar esclarecimento."
            ))

        return RuleResult(
            passed=len(findings) == 0,
            findings=findings
        )
