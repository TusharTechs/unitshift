import unittest
from copy import deepcopy
from decimal import Decimal
from app.fixtures import cases, get_case, reference_contract, context_fingerprint
from app.reconcile import reconcile, naive_review
from app.receipts import digest

class ReconciliationTests(unittest.TestCase):
    def test_declared_decisions_across_adversarial_fixtures(self):
        for case in cases():
            with self.subTest(case=case['id']):
                self.assertEqual(reconcile(case['data'],reference_contract(case))['status'],case['expected'])

    def test_case_conversion_prevents_false_alarm(self):
        case=get_case('case-vs-item'); result=reconcile(case['data'],reference_contract(case))
        self.assertEqual(Decimal(result['payable_minor']),Decimal('30000'))
        self.assertEqual(naive_review(case['data'])['quantity_ratio'],'12')

    def test_split_deliveries_never_multiply_invoice(self):
        case=get_case('join-fanout'); result=reconcile(case['data'],reference_contract(case))
        self.assertEqual(Decimal(result['payable_minor']),Decimal('30000'))
        self.assertEqual(Decimal(naive_review(case['data'])['payable_minor']),Decimal('60000'))

    def test_duplicate_invoice_zeroes_payable(self):
        case=get_case('duplicate-invoice'); result=reconcile(case['data'],reference_contract(case))
        self.assertEqual(result['status'],'held'); self.assertEqual(Decimal(result['payable_minor']),0)

    def test_cumulative_invoice_quantity_cannot_reuse_same_delivery(self):
        case=get_case('case-vs-item'); data=deepcopy(case['data'])
        data['sources']['invoices'][0]['billed_qty']='80'
        data['sources']['invoices'].append(dict(data['sources']['invoices'][0],bill_line='INV-102:L1'))
        result=reconcile(data,reference_contract(case))
        self.assertEqual(result['status'],'held')
        self.assertEqual([r['status'] for r in result['lines']],['supported','held'])
        self.assertEqual(Decimal(result['payable_minor']),Decimal('20000'))

    def test_model_cannot_define_unsupported_conversion(self):
        case=get_case('case-vs-item'); contract=reference_contract(case)
        contract['unit_dictionary']={'CS':'each','EA':'pack'}
        self.assertEqual(reconcile(case['data'],contract)['status'],'held')

    def test_missing_pack_requires_evidence_even_when_model_mapping_exists(self):
        case=get_case('missing-pack')
        self.assertEqual(reconcile(case['data'],reference_contract(case))['status'],'held')
        data=deepcopy(case['data']); data['sources']['purchase_orders'][0]['items_per_carton']='12'
        self.assertEqual(reconcile(data,reference_contract(case))['status'],'supported')

    def test_mapping_fingerprint_expires_on_catalog_change(self):
        first=get_case('case-vs-item')['data']; changed=get_case('catalog-change')['data']
        self.assertNotEqual(context_fingerprint(first),context_fingerprint(changed))
        invoice=deepcopy(first); invoice['sources']['invoices'][0]['billed_qty']='60'
        self.assertEqual(context_fingerprint(first),context_fingerprint(invoice))

    def test_duplicate_mapping_fields_rejected(self):
        case=get_case('case-vs-item'); contract=reference_contract(case)
        contract=deepcopy(contract); contract['fields']['invoices']['price']=contract['fields']['invoices']['quantity']
        self.assertEqual(reconcile(case['data'],contract)['status'],'held')

    def test_nonfinite_amount_is_held(self):
        case=get_case('case-vs-item'); data=deepcopy(case['data'])
        for value in ('NaN','Infinity','-Infinity'):
            data['sources']['invoices'][0]['billed_qty']=value
            self.assertEqual(reconcile(data,reference_contract(case))['status'],'held')

    def test_held_line_preserves_its_actual_currency(self):
        case=get_case('currency-conflict')
        result=reconcile(case['data'],reference_contract(case))
        self.assertEqual(result['lines'][0]['currency'],'EUR')
        self.assertIsNone(result['currency'])

if __name__=='__main__': unittest.main()
