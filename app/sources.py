"""Bounded, read-only Zetaris source tools. No model-supplied SQL is executed."""
import json
import re
from copy import deepcopy
from .config import ROOT, config
from .providers import zetaris_query, ProviderError
from .receipts import receipt

TABLES={'purchase_orders':'UNITSHIFT_PURCHASE.orders','invoices':'UNITSHIFT_INVOICE.invoice_lines','receiving':'UNITSHIFT_RECEIVING.receipts'}

def rows_as_dicts(result):
    headers=result.get('headers'); rows=result.get('data')
    if not isinstance(headers,list) or not all(isinstance(h,str) for h in headers) or len(headers)!=len(set(headers)):
        raise ProviderError('Zetaris response has missing or ambiguous column headers.')
    if not isinstance(rows,list): raise ProviderError('Zetaris response has no tabular data.')
    if len(rows)>=1000: raise ProviderError('Source read reached the row limit; refusing a potentially incomplete review.')
    if any(not isinstance(row,list) or len(row)!=len(headers) for row in rows):
        raise ProviderError('Zetaris response contains an invalid row shape.')
    return [dict(zip(headers,row)) for row in rows]

def load_case_data(case,run_id=None,backend=None):
    backend=backend or config().get('DATA_BACKEND','local')
    if backend=='local': return deepcopy(case['data']),{'label':'Local synthetic fixtures','backend':'local'}
    if backend!='zetaris': raise ValueError('Unknown data backend.')
    case_id=case['id']
    if not re.fullmatch('[a-z0-9-]+',case_id): raise ValueError('Invalid scenario ID.')
    data={k:deepcopy(v) for k,v in case['data'].items() if k!='sources'}
    data['sources']={}
    for source,table in TABLES.items():
        sql=f"SELECT record_json FROM {table} WHERE case_id = '{case_id}' LIMIT 1000"
        rows=rows_as_dicts(zetaris_query(sql,run_id))
        if not rows: raise ProviderError(f'Zetaris source {table} has no records for this case. No local fallback used.')
        decoded=[]
        for row in rows:
            try: record=json.loads(row['record_json'])
            except (json.JSONDecodeError,KeyError,TypeError):
                raise ProviderError(f'Zetaris source {table} contains an invalid record payload.') from None
            if not isinstance(record,dict): raise ProviderError('Source payload must be a record object.')
            decoded.append(record)
        data['sources'][source]=decoded
    manifest_path=ROOT/'data/zetaris-manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    data['source_context']={'backend':'zetaris','tables':TABLES,'prefix':manifest.get('prefix')}
    return data,{'label':'Zetaris · private S3 synthetic exports','backend':'zetaris','tables':TABLES,
                 'storage':{n:s.get('path') for n,s in manifest.get('sources',{}).items()}}

def federated_fanout_check(case_id,run_id=None):
    """Demonstrate the unnormalised invoice grain hazard across two registered sources."""
    if case_id not in ('case-vs-item','join-fanout'): return None
    sql=f"""SELECT COUNT(*) AS joined_rows,
       SUM(CAST(get_json_object(i.record_json, '$.billed_qty') AS DECIMAL(18,4)) *
           CAST(get_json_object(i.record_json, '$.rate_minor_per_billed_uom') AS DECIMAL(18,4))) AS naive_payable_minor
FROM UNITSHIFT_INVOICE.invoice_lines i
JOIN UNITSHIFT_RECEIVING.receipts r
  ON i.case_id = r.case_id
 AND get_json_object(i.record_json, '$.order_ref') = get_json_object(r.record_json, '$.po_number')
WHERE i.case_id = '{case_id}'"""
    rows=rows_as_dicts(zetaris_query(sql,run_id))
    return {'query':sql,'rows':rows,'purpose':'Diagnostic of a deliberately unsafe join, not an approved payable.'}
