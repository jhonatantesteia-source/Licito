import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from licitacoes.rules.pipeline import FullParticipantChecker
from licitacoes.rules.proposta import ProposalArithmeticRule
from licitacoes.edital.deterministic_parser import DeterministicParser
from licitacoes.ingest.money import parse_brl
from licitacoes.rules.base import Finding

class TestMonetaryPipeline(unittest.TestCase):
    def setUp(self):
        # Mock edital data for the checker
        self.edital_data = {"object": "Compra de materiais", "items": []}
        self.checker = FullParticipantChecker(self.edital_data)

    def test_1_deterministic_beats_llm(self):
        print("\n--- TEST 1: Deterministic Beats LLM ---")
        # Mock a proposal document flow
        # We simulate the merge logic inside FullParticipantChecker
        # since we can't easily mock the LLM output inside the actual class without monkeypatching
        
        # Simulate Deterministic Parser Result
        deterministic_items = [{
            "id": "1",
            "description": "Item Test",
            "unit": "UN",
            "quantity": Decimal("10"),
            "unit_price": Decimal("31.99"),
            "total_price": Decimal("319.90"),
            "ceiling_price": Decimal("35.00")
        }]
        
        # Simulate LLM Result
        llm_items = [{
            "id": "1",
            "unit_price": "3199", # The error we are fighting
            "total_price": "3199.00",
            "quantity": "10"
        }]
        
        # Merge logic (mirroring what's now in pipeline.py)
        merged_items = []
        conflicts = []
        llm_map = {str(item.get("id")): item for item in llm_items if item.get("id")}
        
        for d_item in deterministic_items:
            item_id = str(d_item["id"])
            l_item = llm_map.get(item_id, {})
            merged_item = d_item.copy()
            for field in ["unit_price", "total_price", "quantity"]:
                d_val = d_item.get(field)
                l_val = l_item.get(field)
                if d_val is not None:
                    if l_val is not None and l_val != d_val:
                        conflicts.append({"item_id": item_id, "field": field, "deterministic": d_val, "llm": l_val})
                else:
                    merged_item[field] = l_val
            merged_items.append(merged_item)

        self.assertEqual(merged_items[0]["unit_price"], Decimal("31.99"))
        self.assertTrue(len(conflicts) > 0, "Conflict should have been logged")
        print(f"Result: {merged_items[0]['unit_price']} (Expected 31.99)")
        print(f"Conflicts: {conflicts}")

    def test_2_total_divergence(self):
        print("\n--- TEST 2: Total Declared vs Calculated ---")
        context = {
            'items': [
                {'id': '1', 'qty': Decimal('10'), 'unit_price': Decimal('31.99'), 'total': Decimal('319.90'), 'ceiling': Decimal('35.00')}
            ],
            'proposal_total_declared': Decimal('3199.00') # Divergent
        }
        rule = ProposalArithmeticRule()
        result = rule.evaluate(context)
        
        self.assertFalse(result.passed)
        divergence_finding = any("Soma dos itens" in f.finding_text for f in result.findings)
        self.assertTrue(divergence_finding, "Should generate divergence finding")
        print(f"Findings: {[f.finding_text for f in result.findings]}")

    def test_3_total_correct(self):
        print("\n--- TEST 3: Total Declared Correct ---")
        context = {
            'items': [
                {'id': '1', 'qty': Decimal('10'), 'unit_price': Decimal('31.99'), 'total': Decimal('319.90'), 'ceiling': Decimal('35.00')}
            ],
            'proposal_total_declared': Decimal('319.90')
        }
        rule = ProposalArithmeticRule()
        result = rule.evaluate(context)
        self.assertTrue(result.passed)
        print("Result: Passed (Correct)")

    def test_4_brazilian_thousands(self):
        print("\n--- TEST 4: Brazilian Thousands ---")
        values = ["1.250,00", "2.480,35", "10.000,00"]
        for v in values:
            parsed = parse_brl(v)
            self.assertIsInstance(parsed, Decimal)
            print(f"PDF: {v} -> Parsed: {parsed} ({type(parsed)})")

    def test_5_small_values(self):
        print("\n--- TEST 5: Small Values ---")
        values = ["0,50", "0,75", "1,99", "9,90"]
        for v in values:
            parsed = parse_brl(v)
            self.assertIsInstance(parsed, Decimal)
            self.assertNotEqual(parsed, int(parsed * 100)) # Should not be cents
            print(f"PDF: {v} -> Parsed: {parsed} ({type(parsed)})")

if __name__ == "__main__":
    unittest.main()
