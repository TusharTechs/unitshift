import unittest,tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from app.operations_data import OPERATIONS
from app.operations import apply_scenario,simulate,frontier,approve_plan,plan_recovery,interpret_disruption,database,history,ask_operations,checked_operator_brief,operator_workflow_brief

class OperationsTests(unittest.TestCase):
    def test_baseline_covers_only_three_promises(self):
        r=simulate(apply_scenario(OPERATIONS),[])
        self.assertEqual(r['protected_orders'],3)
        self.assertEqual(r['revenue_at_risk_minor'],33400)

    def test_default_recovery_can_protect_every_order_for_212_dollars(self):
        result=frontier(apply_scenario(OPERATIONS))
        self.assertEqual(result['choices'][0]['protected_orders'],6)
        self.assertEqual(result['choices'][0]['cost_minor'],21200)

    def test_supplier_outage_has_a_real_budget_gap(self):
        f=frontier(apply_scenario(OPERATIONS,{'disabled_suppliers':['Harbor Supply']}))
        self.assertEqual(f['choices'][0]['protected_orders'],5)
        self.assertEqual(f['minimum_full_recovery_minor'],24000)
        self.assertEqual(f['budget_gap_minor'],1500)

    def test_late_stock_cannot_protect_an_earlier_deadline(self):
        r=simulate(apply_scenario(OPERATIONS),[{'offer_id':'O-NL-F','packs':4}])
        self.assertTrue(r['valid'])
        self.assertEqual(next(o for o in r['orders'] if o['id']=='SO-2042')['short_units'],40)

    def test_pack_prices_are_not_treated_as_item_prices(self):
        r=simulate(apply_scenario(OPERATIONS),[{'offer_id':'O-HB-F','packs':4}])
        self.assertEqual(r['purchases'][0]['units'],40)
        self.assertEqual(r['cost_minor'],11600)

    def test_model_cannot_override_quote_stock_or_budget(self):
        data=apply_scenario(OPERATIONS)
        self.assertFalse(simulate(data,[{'offer_id':'O-HB-F','packs':5}])['valid'])
        self.assertFalse(simulate(apply_scenario(OPERATIONS,{'budget_minor':10000}),[{'offer_id':'O-HB-F','packs':4}])['valid'])
        with self.assertRaises(ValueError): simulate(data,[{'offer_id':'O-HB-F','packs':4,'cost_minor':1}])

    def test_one_unit_cannot_fulfill_two_customer_orders(self):
        r=simulate(apply_scenario(OPERATIONS),[])
        allocated=sum(o['fulfilled_units'] for o in r['orders'] if o['sku']=='FILTER-01')
        self.assertEqual(allocated,100)

    def test_cash_floor_overrules_a_larger_scenario_budget(self):
        data=apply_scenario(OPERATIONS,{'budget_minor':50000})
        data['operating_policy'][0]['cash_balance_minor']=355000
        r=simulate(data,[{'offer_id':'O-HB-F','packs':2}])
        self.assertFalse(r['valid']);self.assertEqual(r['budget_minor'],5000)

    def test_source_changes_reject_a_previously_proposed_plan(self):
        original=apply_scenario(OPERATIONS,{})
        plan={'status':'proposed','scenario_overrides':{},'context_hash':original['context_hash']}
        changed=deepcopy(OPERATIONS);changed['supplier_offers'][0]['available_packs']=0
        with patch('app.operations.get_plan',return_value=plan),patch('app.operations.load_operations',return_value=changed):
            with self.assertRaisesRegex(ValueError,'Source facts changed'): approve_plan('a'*32)

    def test_scenario_controls_do_not_mutate_source_records(self):
        original=deepcopy(OPERATIONS)
        apply_scenario(OPERATIONS,{'inbound_units':120,'disabled_suppliers':['Harbor Supply']})
        self.assertEqual(OPERATIONS,original)


    def test_explicit_dollar_budget_cannot_become_cents(self):
        wrong_model='{"overrides":{"budget_minor":225,"inbound_units":80,"disabled_suppliers":["Harbor Supply"]}}'
        with patch('app.operations.load_operations',return_value=deepcopy(OPERATIONS)),patch('app.operations.chat',return_value=wrong_model),patch('app.operations.receipt'):
            result=interpret_disruption('Harbor is unavailable; spend at most $225.',{'budget_minor':22500,'inbound_units':80,'disabled_suppliers':[]})
        self.assertEqual(result['overrides']['budget_minor'],22500)
        self.assertIn('225.00',result['interpretation'])

    def test_ambiguous_money_note_preserves_budget_and_asks(self):
        proposal='{"overrides":{"budget_dollars":"100","inbound_units":80,"disabled_suppliers":[]}}'
        with patch('app.operations.load_operations',return_value=deepcopy(OPERATIONS)),patch('app.operations.chat',return_value=proposal),patch('app.operations.receipt'):
            result=interpret_disruption('The order is $100; the quote is $200.',{'budget_minor':22500,'inbound_units':80,'disabled_suppliers':[]})
        self.assertEqual(result['overrides']['budget_minor'],22500)
        self.assertTrue(result['questions'])

    def test_unknown_interpreted_supplier_is_rejected(self):
        proposal='{"overrides":{"inbound_units":80,"disabled_suppliers":["Invented Supplier"]}}'
        with patch('app.operations.load_operations',return_value=deepcopy(OPERATIONS)),patch('app.operations.chat',return_value=proposal),patch('app.operations.receipt'):
            with self.assertRaises(ValueError): interpret_disruption('Avoid the supplier.',{'budget_minor':22500,'inbound_units':80,'disabled_suppliers':[]})


    def test_repeated_drafting_is_idempotent_and_history_is_authoritative(self):
        import json
        data=apply_scenario(OPERATIONS,{})
        result=frontier(data)['choices'][0]
        plan={'id':'a'*32,'created_at':'2026-10-27T00:00:00Z','scenario_overrides':{},'context_hash':data['context_hash'],
              'simulation':result,'frontier':{'choices':[result]},'memory_scope':'test-scope','operator_brief':'All necessary prerequisites are complete for the next stage.','proposal':{'headline':'Test'}}
        with tempfile.TemporaryDirectory() as folder,patch('app.operations.ROOT',Path(folder)),patch('app.operations.load_operations',return_value=deepcopy(OPERATIONS)),patch('app.operations.memory_call',return_value={'id':'mem-test'}),patch('app.operations.receipt'):
            with database() as db: db.execute('INSERT INTO plans VALUES (?,?,?,?)',(plan['id'],plan['created_at'],json.dumps(plan),'proposed'))
            approve_plan(plan['id']);first=history()
            approve_plan(plan['id']);second=history()
            self.assertEqual(len(first['actions']),6)
            self.assertEqual(len(second['actions']),6)
            self.assertEqual(second['plans'][0]['status'],'drafted')
            self.assertIsNone(second['plans'][0]['operator_brief'])

    def test_partial_recovery_drafts_a_residual_risk_escalation(self):
        import json
        controls={'disabled_suppliers':['Harbor Supply']}
        data=apply_scenario(OPERATIONS,controls);result=frontier(data)['choices'][0]
        plan={'id':'b'*32,'created_at':'2026-10-27T00:00:00Z','scenario_overrides':controls,'context_hash':data['context_hash'],
              'simulation':result,'frontier':{'choices':[result]},'memory_scope':'test-scope','operator_brief':'All necessary prerequisites are complete for the next stage.','proposal':{'headline':'Test'}}
        with tempfile.TemporaryDirectory() as folder,patch('app.operations.ROOT',Path(folder)),patch('app.operations.load_operations',return_value=deepcopy(OPERATIONS)),patch('app.operations.memory_call',return_value={'id':'mem-test'}),patch('app.operations.receipt'):
            with database() as db: db.execute('INSERT INTO plans VALUES (?,?,?,?)',(plan['id'],plan['created_at'],json.dumps(plan),'proposed'))
            approve_plan(plan['id']);actions=history()['actions']
            self.assertEqual(len(actions),5)
            self.assertTrue(any(a['title'].startswith('Escalate') for a in actions))


    def test_copilot_uses_verified_deadline_facts_instead_of_model_prose(self):
        data=deepcopy(OPERATIONS);data['provenance']={'source_run_id':'test'}
        route='{"query_type":"deadline_tradeoff","sku":"FILTER-01","supplier":null,"order_id":null}'
        with patch('app.operations.load_operations',return_value=data),patch('app.operations.chat',return_value=route),patch('app.operations.receipt'):
            result=ask_operations('Why not buy the cheapest filter?')
        self.assertIn('SO-2042',result['answer'])
        self.assertIn('is too late',result['answer'])
        self.assertIn('Already supported by verified stock: SO-2041',result['answer'])

    def test_copilot_rejects_a_fabricated_reference(self):
        data=deepcopy(OPERATIONS);data['provenance']={'source_run_id':'test'}
        route='{"query_type":"order_snapshot","sku":null,"supplier":null,"order_id":"SO-INVENTED"}'
        with patch('app.operations.load_operations',return_value=data),patch('app.operations.chat',return_value=route),patch('app.operations.receipt'):
            with self.assertRaisesRegex(Exception,'unknown order'): ask_operations('Inspect an order.')

    def test_persisted_old_brief_cannot_bypass_current_guidance_checks(self):
        self.assertIsNone(checked_operator_brief('All necessary prerequisites are complete for the next stage.','ready'))
        self.assertIsNone(checked_operator_brief('Review all protected orders.','partial'))
        self.assertEqual(checked_operator_brief('Review the proposed purchase drafts.','ready'),'Review the proposed purchase drafts.')

    def test_nightshift_followup_cannot_contradict_verified_plan_status(self):
        self.assertIsNone(operator_workflow_brief({'risk_label':'ready','next_action':'review_purchase_drafts'},'partial'))
        self.assertIsNone(operator_workflow_brief({'risk_label':'ready','next_action':'send_supplier_order'},'ready'))
        self.assertIn('purchase drafts',operator_workflow_brief({'risk_label':'ready','next_action':'review_purchase_drafts'},'ready'))

if __name__=='__main__': unittest.main()
