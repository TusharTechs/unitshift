"""Reproducible same-model comparison. Reports observed results, including errors.

The comparison isolates adaptive mapping discovery; both methods share identical
deterministic payment invariants. It does not establish those invariants' value
over a direct LLM payment answer, nor prove an advantage when the scores tie.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.fixtures import cases
from app.agent import run_review
from app.receipts import ROOT,load_receipts

def evaluate(case,mode,backend):
    expected_amount=Decimal('30000') if case['expected']=='supported' else Decimal(0)
    item={'case':case['id'],'mode':mode,'expected_status':case['expected'],'expected_payable_minor':str(expected_amount)}
    try:
        run=run_review(case['id'],mode=mode,remember=False,backend=backend)
        result=run['result'];calls=[r['details'] for r in load_receipts(run['run_id']) if r['kind']=='model_call']
        item.update(status=result['status'],payable_minor=result['payable_minor'],run_id=run['run_id'],elapsed_s=run['elapsed_s'],
            correct=result['status']==case['expected'] and Decimal(result['payable_minor'])==expected_amount,
            false_approval=result['status']=='supported' and case['expected']=='held',
            prompt_tokens=sum(c.get('usage',{}).get('prompt_tokens',0) for c in calls),
            completion_tokens=sum(c.get('usage',{}).get('completion_tokens',0) for c in calls),model_calls=len(calls))
    except Exception as error:
        item.update(correct=False,error=str(error))
    return item

def main():
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['local','zetaris'],default='zetaris');p.add_argument('--split',default='heldout');args=p.parse_args()
    selected=[c for c in cases() if c['split']==args.split]
    output={'at':datetime.now(timezone.utc).isoformat(),'synthetic':True,'backend':args.backend,'case_count':len(selected),
        'scope':'Same Nemotron model; agent mapping vs one-pass mapping; both share payment invariants; memory disabled.',
        'results':[],'summary':{}}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(evaluate,c,mode,args.backend) for c in selected for mode in ('agent','onepass')]
        for future in as_completed(futures):
            row=future.result();output['results'].append(row)
            print(row['mode'],row['case'],'PASS' if row['correct'] else 'FAIL',flush=True)
    for mode in ('agent','onepass'):
        rows=[r for r in output['results'] if r['mode']==mode]
        output['summary'][mode]={'correct':sum(r['correct'] for r in rows),'total':len(rows),
             'false_approvals':sum(r.get('false_approval',False) for r in rows),'errors':sum('error' in r for r in rows),
             'mean_elapsed_s':round(sum(r.get('elapsed_s',0) for r in rows)/len(rows),2) if rows else 0}
    path=ROOT/'data/evaluation.json';path.write_text(json.dumps(output,indent=2))
    print(json.dumps(output['summary'],indent=2))

if __name__=='__main__': main()
