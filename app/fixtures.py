"""Disclosed synthetic supplier records. Expected decisions are never sent to a model."""
from copy import deepcopy
from .receipts import digest

FIELDS = {
    'purchase_orders': {'id': 'order_line', 'po': 'purchase_order', 'sku': 'internal_part',
        'alias': 'vendor_part', 'quantity': 'ordered_qty', 'unit': 'order_uom',
        'pack': 'items_per_carton', 'price': 'cost_minor_per_item', 'currency': 'iso_currency'},
    'invoices': {'id': 'bill_line', 'po': 'order_ref', 'sku': 'supplier_part',
        'quantity': 'billed_qty', 'unit': 'billed_uom', 'price': 'rate_minor_per_billed_uom', 'currency': 'currency_code'},
    'receiving': {'id': 'receipt_line', 'po': 'po_number', 'sku': 'warehouse_part',
        'quantity': 'received_qty', 'unit': 'stock_uom'},
}
DICT = {'CS': 'pack', 'EA': 'each'}

def base():
    return {
        'supplier': 'Northline Supplies', 'revision': 'catalog-2026-10-v1', 'unit_dictionary': DICT.copy(),
        'sources': {
            'purchase_orders': [{'order_line': 'POL-1', 'purchase_order': 'PO-2048', 'internal_part': 'FILTER-01',
                'vendor_part': 'NL-FLT-12', 'ordered_qty': '10', 'order_uom': 'CS', 'items_per_carton': '12',
                'cost_minor_per_item': '250', 'iso_currency': 'USD'}],
            'invoices': [{'bill_line': 'INV-101:L1', 'order_ref': 'PO-2048', 'supplier_part': 'NL-FLT-12',
                'billed_qty': '120', 'billed_uom': 'EA', 'rate_minor_per_billed_uom': '250', 'currency_code': 'USD'}],
            'receiving': [{'receipt_line': 'GRN-1', 'po_number': 'PO-2048', 'warehouse_part': 'FILTER-01',
                'received_qty': '120', 'stock_uom': 'EA'}]
        }
    }

def cases():
    out = []
    def add(slug, title, description, data, expected, split='heldout'):
        out.append({'id': slug, 'title': title, 'description': description, 'split': split,
                    'data': deepcopy(data), 'expected': expected})
    d=base()
    add('case-vs-item', 'The twelvefold false alarm', 'The order counts cartons. The invoice counts items. Is there actually an overcharge?', d, 'supported', 'demo')
    d=base(); d['sources']['invoices'][0].update(billed_qty='10', billed_uom='CS', rate_minor_per_billed_uom='3000')
    add('carton-priced', 'One carton, twelve items', 'Invoice price applies to a carton, not to one item.', d, 'supported', 'development')
    d=base(); d['sources']['receiving'][0]['received_qty']='60'
    d['sources']['receiving'].append(dict(d['sources']['receiving'][0],receipt_line='GRN-2'))
    add('join-fanout', 'The duplicated payable', 'Two legitimate deliveries repeat one invoice line in a naïve join.', d, 'supported', 'demo')
    d=base(); d['sources']['invoices'][0]['rate_minor_per_billed_uom']='300'
    add('price-rise', 'A real price discrepancy', 'Unit conversion must not hide an actual price increase.', d, 'held')
    d=base(); d['sources']['receiving'][0]['received_qty']='80'
    add('short-delivery', 'Only part of the shipment arrived', 'An apparently valid invoice is not fully backed by delivered quantity.', d, 'held')
    d=base(); d['sources']['purchase_orders'][0]['items_per_carton']=None
    add('missing-pack', 'Ask one useful question', 'The order uses cartons but the conversion is absent. Hold until the operator supplies evidence.', d, 'held', 'demo')
    d=base(); d['sources']['invoices'][0]['currency_code']='EUR'
    add('currency-conflict', 'Same number, different money', 'No invented exchange rate may bridge a currency mismatch.', d, 'held')
    d=base(); d['sources']['receiving'].append(deepcopy(d['sources']['receiving'][0]))
    add('duplicate-receipt', 'A duplicated delivery record', 'Repeating a receipt ID must not manufacture delivered stock.', d, 'held')
    d=base(); d['sources']['invoices'].append(deepcopy(d['sources']['invoices'][0]))
    add('duplicate-invoice', 'The same line billed twice', 'Duplicate invoice identity is held rather than silently deduplicated.', d, 'held')
    d=base(); d['sources']['invoices'][0]['supplier_part']='UNKNOWN-PART'
    add('unknown-sku', 'An unsupported product match', 'Similar-looking descriptions cannot establish product identity.', d, 'held')
    d=base(); d['sources']['invoices'][0]['billed_qty']='-5'
    add('negative-quantity', 'A credit needs its own workflow', 'Negative quantities are outside this payment-review scope.', d, 'held')
    d=base(); d['sources']['invoices'][0].update(billed_qty='132')
    d['sources']['receiving'][0]['received_qty']='132'
    add('over-order', 'Delivered more than authorised', 'Delivered quantity alone does not authorise more than the order.', d, 'held')
    d=base(); d['sources']['invoices'][0]['billed_uom']='PALLET'
    add('unknown-uom', 'An undefined packaging unit', 'An unsupported unit must trigger a hold.', d, 'held')
    d=base(); d['sources']['invoices'][0]['billed_qty']='0'
    add('zero-quantity', 'An empty invoice line', 'Zero quantity cannot produce a supported payable.', d, 'held')
    d=base(); d['revision']='catalog-2026-10-v2'; d['sources']['purchase_orders'][0]['items_per_carton']='24'
    d['sources']['purchase_orders'][0]['ordered_qty']='5'
    add('catalog-change', 'Yesterday’s mapping expired', 'The source revision changes carton size. Prior memory must not supply the old conversion.', d, 'supported', 'development')
    d=base(); mapping={}
    for name, fields in FIELDS.items():
        mapping[name]={semantic: 'x_'+str(i)+'_'+name[:2] for i,semantic in enumerate(fields)}
        d['sources'][name]=[{mapping[name][semantic]: row[field] for semantic,field in fields.items()} for row in d['sources'][name]]
    add('renamed-columns', 'The export schema changed', 'The same task arrives under different field names, with declared schema descriptions.', d, 'supported')
    out[-1]['field_descriptions']=mapping
    d=base(); d['sources']['invoices'][0]['rate_minor_per_billed_uom']='2.5'
    add('fractional-minor', 'Sub-cent price precision', 'Fractional minor-unit values are unsupported in this bounded workflow.', d, 'held')
    d=base(); d['sources']['invoices'][0]['order_ref']='PO-9999'
    add('wrong-order', 'The right SKU on the wrong order', 'Matching a supplier part does not establish purchase-order authorisation.', d, 'held')
    return out

def get_case(case_id):
    return next((c for c in cases() if c['id']==case_id), None)

def reference_contract(case):
    return {'fields': case.get('field_descriptions', FIELDS), 'unit_dictionary': case['data']['unit_dictionary'],
            'evidence': 'Reference mapping used only for deterministic engine tests; not a model result.'}

def context_fingerprint(data):
    # Only the shape and supplier catalogue revision define a mapping scope, never invoice quantity.
    return digest({'supplier':data['supplier'],'revision':data['revision'], 'unit_dictionary':data['unit_dictionary'],
                   'source_context':data.get('source_context',{'backend':'local'}),
                   'schema':{name:sorted({key for row in rows for key in row}) for name,rows in data['sources'].items()}})
