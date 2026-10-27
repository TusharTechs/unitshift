import json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from app.replay import validate_decision,verify_case,public_rate_limit,pennies
from app.config import ROOT
from app.providers import ProviderError

class PublicEvidenceTests(unittest.TestCase):
 def setUp(self):
  self.case=deepcopy(json.loads((ROOT/'data/public/snapshot.json').read_text())['cases'][0])
  for r in self.case['evidence']:
   r['gbp_per_eur']='0.85315';r['calculated_eur']=str(__import__('decimal').Decimal(r['line_amount'])/__import__('decimal').Decimal('0.85315'))
  self.decision={'disposition':'review_required','case_kind':'cancellation','candidate_source_row':540423,'evidence_source_rows':[540423,540424],'missing_evidence':['original_invoice_reference','payment_settlement','refund_authorisation'],'fx_operation':'gbp_divided_by_gbp_per_eur'}
 def test_actual_two_record_candidate_does_not_become_an_authorised_refund(self):
  r=validate_decision(self.decision,self.case)
  self.assertEqual(r['disposition'],'review_required')
  self.assertEqual(pennies(sum(__import__('decimal').Decimal(r['line_amount']) for r in self.case['evidence'])),0)
 def test_an_invented_source_row_cannot_support_a_link(self):
  self.decision['candidate_source_row']=123456
  with self.assertRaises(ValueError):validate_decision(self.decision,self.case)
 def test_settlement_or_authorisation_cannot_be_omitted(self):
  self.decision['missing_evidence']=['original_invoice_reference']
  r=validate_decision(self.decision,self.case)
  self.assertIn('refund_authorisation',r['missing_evidence'])
  self.assertIn('payment_settlement',r['policy_added_missing_evidence'])
 def test_model_cannot_approve_a_refund_from_historical_attributes(self):
  self.decision['disposition']='refund_approved'
  with self.assertRaisesRegex(ValueError,'cannot authorise'):validate_decision(self.decision,self.case)
 def test_the_candidate_must_be_a_cited_source_row(self):
  self.decision['evidence_source_rows']=[540424]
  with self.assertRaisesRegex(ValueError,'must be cited'):validate_decision(self.decision,self.case)
 def test_future_transactions_cannot_be_original_candidates(self):
  self.case['evidence'][1]['invoice_date']='2011-12-10T00:00:00'
  with self.assertRaisesRegex(ValueError,'chronology'):validate_decision(self.decision,self.case)
 def test_a_missing_identity_cannot_be_guessed(self):
  self.case['evidence'][0]['customer_id']=''
  with self.assertRaisesRegex(ValueError,'customer'):validate_decision(self.decision,self.case)
 def test_fx_quote_direction_is_checked(self):
  self.decision['fx_operation']='gbp_multiplied_by_rate'
  with self.assertRaisesRegex(ValueError,'divide'):validate_decision(self.decision,self.case)
 def test_semantic_join_fanout_is_rejected_even_with_the_same_ids(self):
  rows=self.case['evidence']+[self.case['evidence'][0]]
  with patch('app.replay.query',return_value=rows),patch('app.replay.receipt'):
   with self.assertRaises(ProviderError):verify_case(self.case,'a'*32)
 def test_stale_or_changed_source_prices_are_rejected(self):
  rows=deepcopy(self.case['evidence']);rows[0]['unit_price']='0.01'
  with patch('app.replay.query',return_value=rows),patch('app.replay.receipt'):
   with self.assertRaisesRegex(ProviderError,'changed'):verify_case(self.case,'b'*32)
 def test_inverted_semantic_fx_values_are_rejected(self):
  rows=deepcopy(self.case['evidence']);rows[0]['calculated_eur']='-143000'
  with patch('app.replay.query',return_value=rows),patch('app.replay.receipt'):
   with self.assertRaisesRegex(ProviderError,'FX calculation'):verify_case(self.case,'c'*32)
 def test_public_model_allowance_is_persisted_and_bounded(self):
  with tempfile.TemporaryDirectory() as folder,patch('app.replay.ROOT',Path(folder)),patch('app.replay.config',return_value={'UNITSHIFT_PUBLIC_DEMO':'1'}):
   for _ in range(12):public_rate_limit('203.0.113.10')
   with self.assertRaisesRegex(ValueError,'daily'):public_rate_limit('203.0.113.10')

 def test_a_repeated_cancellation_can_link_its_matching_repeated_row(self):
  case=deepcopy(next(c for c in json.loads((ROOT/'data/public/snapshot.json').read_text())['cases'] if c['kind']=='duplicate'))
  d={'disposition':'review_required','case_kind':'duplicate','candidate_source_row':case['evidence'][0]['exact_duplicate_of'],'evidence_source_rows':[r['source_row'] for r in case['evidence']],'missing_evidence':['invoice_confirmation'],'fx_operation':'gbp_divided_by_gbp_per_eur'}
  self.assertEqual(validate_decision(d,case)['case_kind'],'duplicate')
 def test_a_duplicate_link_cannot_hide_a_changed_invoice_field(self):
  case=deepcopy(next(c for c in json.loads((ROOT/'data/public/snapshot.json').read_text())['cases'] if c['kind']=='duplicate'))
  d={'disposition':'review_required','case_kind':'duplicate','candidate_source_row':case['evidence'][0]['exact_duplicate_of'],'evidence_source_rows':[r['source_row'] for r in case['evidence']],'missing_evidence':['invoice_confirmation'],'fx_operation':'gbp_divided_by_gbp_per_eur'}
  case['evidence'][1]['quantity']+=1
  with self.assertRaisesRegex(ValueError,'source fields'):validate_decision(d,case)

if __name__=='__main__':unittest.main()
