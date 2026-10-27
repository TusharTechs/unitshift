"""Payment-review invariants. Model text cannot override these checks."""
from collections import Counter
from decimal import Decimal, InvalidOperation
from .fixtures import FIELDS
from .receipts import digest

class Hold(Exception):
    pass

def number(value, label, integer=False):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise Hold(f'Missing or invalid {label}.')
    if not value.is_finite() or value <= 0 or (integer and value != value.to_integral_value()):
        raise Hold(f'{label} must be a positive {"integer" if integer else "number"}.')
    if value > Decimal('1000000000000'):
        raise Hold(f'{label} exceeds the supported limit.')
    return value

def validate_contract(data, contract):
    if not isinstance(contract, dict) or not isinstance(contract.get('fields'), dict):
        raise Hold('No valid semantic contract was returned.')
    if contract.get('unit_dictionary') != data['unit_dictionary']:
        raise Hold('Unit meanings must exactly match the supplied source dictionary.')
    for source, required in FIELDS.items():
        mapping=contract['fields'].get(source)
        if not isinstance(mapping, dict) or set(mapping) != set(required):
            raise Hold(f'Contract fields for {source} are incomplete.')
        values=list(mapping.values())
        if not all(isinstance(v,str) for v in values) or len(set(values)) != len(values):
            raise Hold(f'Contract for {source} maps distinct meanings to the same field.')
        keys={key for row in data['sources'][source] for key in row}
        if not set(values).issubset(keys):
            raise Hold(f'Contract references fields absent from {source}.')

def reconcile(data, contract):
    try:
        validate_contract(data, contract)
    except Hold as error:
        return {'status':'held','payable_minor':'0','currency':None,'lines':[], 'issues':[str(error)],'checks':[]}
    fields=contract['fields']
    tables={name:[{meaning:row.get(field) for meaning,field in fields[name].items()} for row in rows]
            for name,rows in data['sources'].items()}
    duplicate_sources=[]
    for name,rows in tables.items():
        ids=[str(row['id']) for row in rows]
        if len(ids)!=len(set(ids)) or any(row['id'] in (None,'') for row in rows):
            duplicate_sources.append(name)
    lines=[]; total=Decimal(0); currencies=set(); allocations=Counter()
    def units(qty, code, po):
        qty=number(qty,'quantity')
        meaning=data['unit_dictionary'].get(str(code))
        if meaning=='each': return qty
        if meaning=='pack': return qty * number(po['pack'],'items per pack',True)
        raise Hold(f'Unit {code!s} has no supplied definition.')
    for invoice in tables['invoices']:
        line={'id':invoice['id'],'sku':invoice['sku'],'currency':invoice['currency'],'status':'held','claimed_minor':None,'supported_minor':'0','issues':[], 'checks':[]}
        try:
            qty=number(invoice['quantity'],'invoice quantity')
            rate=number(invoice['price'],'invoice price in minor units',True)
            line['claimed_minor']=str(qty*rate)
            if duplicate_sources:
                raise Hold('Duplicate or missing record IDs in '+', '.join(duplicate_sources)+'.')
            matches=[po for po in tables['purchase_orders'] if po['alias']==invoice['sku'] and po['po']==invoice['po']]
            if len(matches)!=1:
                raise Hold('No unique authorised product and purchase-order match.')
            po=matches[0]
            if not invoice['currency'] or invoice['currency']!=po['currency']:
                raise Hold('Invoice and order currencies disagree; no FX rate is assumed.')
            currencies.add(str(invoice['currency']))
            iq=units(qty,invoice['unit'],po)
            oq=units(po['quantity'],po['unit'],po)
            receipts=[r for r in tables['receiving'] if r['sku']==po['sku'] and r['po']==po['po']]
            if not receipts: raise Hold('No matching receiving evidence.')
            rq=sum((units(r['quantity'],r['unit'],po) for r in receipts),Decimal(0))
            allocations[(po['po'],po['id'])]+=iq
            allocated=allocations[(po['po'],po['id'])]
            if allocated>oq: raise Hold('Cumulative invoiced quantity exceeds the authorised order.')
            if allocated>rq: raise Hold('Cumulative invoiced quantity exceeds supported deliveries.')
            expected=iq*number(po['price'],'authorised item price in minor units',True)
            claimed=qty*rate
            if claimed>Decimal('9007199254740991') or total+claimed>Decimal('9007199254740991'):
                raise Hold('Payable exceeds the supported exact display range.')
            if claimed!=expected: raise Hold('Billed amount differs from the unit-normalised authorised amount.')
            if claimed!=claimed.to_integral_value(): raise Hold('Payable contains a fractional minor unit.')
            line.update(status='supported',supported_minor=str(claimed),currency=invoice['currency'],
                        normalised_items=str(iq),authorised_items=str(oq),received_items=str(rq),
                        receipt_ids=[r['id'] for r in receipts],po_line=po['id'])
            line['checks']=['Unique invoice / order / delivery IDs','Exact product and order match',
                            'Source-backed unit conversion','Cumulative quantity within order and deliveries',
                            'Exact currency and minor-unit arithmetic','Invoice counted once, deliveries aggregated separately']
            total+=claimed
        except Hold as error:
            line['issues'].append(str(error))
        lines.append(line)
    if len(currencies)>1:
        for line in lines:
            line.update(status='held',supported_minor='0')
            line['issues'].append('Mixed-currency batch requires separate reviews.')
        total=Decimal(0)
    held=any(line['status']=='held' for line in lines) or not lines
    return {'status':'held' if held else 'supported','payable_minor':str(total),
            'currency':next(iter(currencies)) if len(currencies)==1 else None,'lines':lines,
            'issues':[],'checks':['Decimal arithmetic','Read-only review; no payment executed'],
            'source_hash':digest(data),'contract_hash':digest(contract)}

def naive_review(data):
    # Deliberately disclosed weak baseline: known fixture field names, unnormalised quantities,
    # and an invoice-to-deliveries join without preserving invoice grain.
    try:
        po=data['sources']['purchase_orders'][0]; inv=data['sources']['invoices'][0]
        n=len([r for r in data['sources']['receiving'] if r.get('po_number')==inv.get('order_ref')])
        amount=Decimal(str(inv['billed_qty']))*Decimal(str(inv['rate_minor_per_billed_uom']))*max(1,n)
        ratio=Decimal(str(inv['billed_qty']))/Decimal(str(po['ordered_qty']))
        return {'payable_minor':str(amount),'quantity_ratio':str(ratio),'joined_rows':n,
                'warning':'Quantities use different units and joined rows may repeat the invoice. This is a weak baseline, not a production matcher.'}
    except (KeyError,InvalidOperation,ZeroDivisionError):
        return {'payable_minor':None,'warning':'Name-based baseline cannot interpret this schema.'}
