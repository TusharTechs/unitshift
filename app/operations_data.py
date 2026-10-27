"""Disclosed operational scenario: a distributor, six customer promises, three shortages."""
OPERATIONS = {
 'customer_orders':[
  {'id':'SO-2041','customer':'Forma Facilities','sku':'FILTER-01','product':'Flow filters','quantity':80,'due_hours':12,'unit_revenue_minor':480,'priority':'Critical','destination':'Brooklyn'},
  {'id':'SO-2042','customer':'Common Ground','sku':'FILTER-01','product':'Flow filters','quantity':60,'due_hours':24,'unit_revenue_minor':480,'priority':'High','destination':'Queens'},
  {'id':'SO-2043','customer':'Eastline Supply','sku':'GLOVE-02','product':'Work gloves','quantity':160,'due_hours':18,'unit_revenue_minor':210,'priority':'High','destination':'Jersey City'},
  {'id':'SO-2044','customer':'Fieldwork Studio','sku':'GLOVE-02','product':'Work gloves','quantity':120,'due_hours':30,'unit_revenue_minor':210,'priority':'Standard','destination':'Manhattan'},
  {'id':'SO-2045','customer':'Sunday Coffee','sku':'CUP-03','product':'Compostable cups','quantity':300,'due_hours':24,'unit_revenue_minor':32,'priority':'Standard','destination':'Brooklyn'},
  {'id':'SO-2046','customer':'Gather Collective','sku':'CUP-03','product':'Compostable cups','quantity':200,'due_hours':48,'unit_revenue_minor':32,'priority':'Standard','destination':'Manhattan'},
 ],
 'inventory':[
  {'sku':'FILTER-01','product':'Flow filters','on_hand_units':20,'verified_inbound_units':80,'expected_inbound_units':120,'source_reference':'UNITSHIFT_RECEIVING.receipts / short-delivery','warehouse':'Northline · NYC','unit_cost_minor':250},
  {'sku':'GLOVE-02','product':'Work gloves','on_hand_units':220,'verified_inbound_units':0,'expected_inbound_units':60,'source_reference':'Warehouse count / cycle-142','warehouse':'Northline · NYC','unit_cost_minor':120},
  {'sku':'CUP-03','product':'Compostable cups','on_hand_units':450,'verified_inbound_units':0,'expected_inbound_units':50,'source_reference':'Warehouse count / cycle-142','warehouse':'Northline · NYC','unit_cost_minor':18},
 ],
 'supplier_offers':[
  {'id':'O-NL-F','supplier':'Northline Direct','sku':'FILTER-01','pack_units':10,'pack_price_minor':2450,'available_packs':4,'lead_hours':36,'region':'Newark, NJ','terms':'Prepaid','quote_ref':'Q-401','on_time_shipments':17,'total_shipments':20},
  {'id':'O-HB-F','supplier':'Harbor Supply','sku':'FILTER-01','pack_units':10,'pack_price_minor':2900,'available_packs':4,'lead_hours':18,'region':'Hoboken, NJ','terms':'Prepaid','quote_ref':'Q-402','on_time_shipments':28,'total_shipments':30},
  {'id':'O-SM-F','supplier':'Summit Industrial','sku':'FILTER-01','pack_units':20,'pack_price_minor':6300,'available_packs':2,'lead_hours':6,'region':'Brooklyn, NY','terms':'Prepaid','quote_ref':'Q-403','on_time_shipments':19,'total_shipments':20},
  {'id':'O-HB-G','supplier':'Harbor Supply','sku':'GLOVE-02','pack_units':20,'pack_price_minor':2800,'available_packs':3,'lead_hours':12,'region':'Hoboken, NJ','terms':'Prepaid','quote_ref':'Q-404','on_time_shipments':28,'total_shipments':30},
  {'id':'O-SM-G','supplier':'Summit Industrial','sku':'GLOVE-02','pack_units':20,'pack_price_minor':3300,'available_packs':3,'lead_hours':6,'region':'Brooklyn, NY','terms':'Prepaid','quote_ref':'Q-405','on_time_shipments':19,'total_shipments':20},
  {'id':'O-NL-G','supplier':'Northline Direct','sku':'GLOVE-02','pack_units':20,'pack_price_minor':2200,'available_packs':3,'lead_hours':48,'region':'Newark, NJ','terms':'Prepaid','quote_ref':'Q-406','on_time_shipments':17,'total_shipments':20},
  {'id':'O-HB-C','supplier':'Harbor Supply','sku':'CUP-03','pack_units':25,'pack_price_minor':600,'available_packs':2,'lead_hours':24,'region':'Hoboken, NJ','terms':'Prepaid','quote_ref':'Q-407','on_time_shipments':28,'total_shipments':30},
  {'id':'O-SM-C','supplier':'Summit Industrial','sku':'CUP-03','pack_units':25,'pack_price_minor':750,'available_packs':2,'lead_hours':12,'region':'Brooklyn, NY','terms':'Prepaid','quote_ref':'Q-408','on_time_shipments':19,'total_shipments':20},
 ],
 'operating_policy':[{'id':'POLICY-01','workspace':'Northline Supply Co.','currency':'USD','recovery_budget_minor':22500,
      'cash_balance_minor':410000,'cash_floor_minor':350000,'revision':'operations-2026-10-27-v1',
      'objective':'Protect customer quantities by their deadlines, then minimise incremental purchase cost.',
      'execution':'Sandbox only. Purchase drafts and customer notes are not sent to external parties.'}]
}

OPS_SOURCES={
 'customer_orders':{'database':'UNITSHIFT_DEMAND','table':'customer_orders','format':'CSV','filename':'customer_orders.csv'},
 'inventory':{'database':'UNITSHIFT_STOCK','table':'inventory','format':'JSON','filename':'inventory.json'},
 'supplier_offers':{'database':'UNITSHIFT_MARKET','table':'supplier_offers','format':'JSON','filename':'supplier_offers.json'},
 'operating_policy':{'database':'UNITSHIFT_POLICY','table':'operating_policy','format':'JSON','filename':'operating_policy.json'},
}
