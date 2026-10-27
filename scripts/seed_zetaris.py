"""Publish disclosed synthetic exports and register scoped Zetaris file sources.

Uses the existing AWS identity and private workspace bucket. Never creates IAM
credentials, changes bucket access, overwrites another application prefix, or drops tables.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import os

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT
from app.fixtures import cases
from app.providers import zetaris_query
from app.operations_data import OPERATIONS,OPS_SOURCES

SOURCES={
    'purchase_orders': {'database':'UNITSHIFT_PURCHASE','table':'orders','format':'CSV','filename':'purchase_orders.csv'},
    'invoices': {'database':'UNITSHIFT_INVOICE','table':'invoice_lines','format':'JSON','filename':'invoices.json'},
    'receiving': {'database':'UNITSHIFT_RECEIVING','table':'receipts','format':'JSON','filename':'receiving.json'},
}
SOURCES.update(OPS_SOURCES)

def aws(*args):
    return subprocess.run(['aws',*args,'--region','us-west-1'],capture_output=True,text=True,check=True).stdout

def export_sources():
    folder=ROOT/'data/exports'; folder.mkdir(parents=True,exist_ok=True)
    for name,source in SOURCES.items():
        records=([{'case_id':'operations','record_json':json.dumps(row,separators=(',',':'))} for row in OPERATIONS[name]]
                 if name in OPERATIONS else
                 [{'case_id':c['id'],'record_json':json.dumps(row,separators=(',',':'))}
                  for c in cases() for row in c['data']['sources'][name]])
        target=folder/source['filename']
        if source['format']=='CSV':
            with target.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=['case_id','record_json']);writer.writeheader();writer.writerows(records)
        else:
            target.write_text(json.dumps(records,indent=2)+'\n')
    return folder

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    folder=export_sources()
    resources=json.loads(aws('cloudformation','describe-stack-resources','--stack-name','zetaris-UnitShift-Hackathon-AWS-5990892f',
                             '--query','StackResources[?LogicalResourceId==`WorkspaceS3Bucket`].PhysicalResourceId','--output','json'))
    if len(resources)!=1: raise RuntimeError('Expected exactly one existing workspace bucket.')
    bucket=resources[0]
    manifest={'bucket':bucket,'prefix':'unitshift/v1','sources':SOURCES,'synthetic':True,
              'expected_row_counts':{name:(len(OPERATIONS[name]) if name in OPERATIONS else sum(len(c['data']['sources'][name]) for c in cases())) for name in SOURCES}}
    plan=[]
    for name,source in SOURCES.items():
        source['path']=f"s3a://{bucket}/unitshift/v1/{source['filename']}"
        plan.append(f'CREATE LIGHTNING DATABASE {source["database"]} DESCRIBE BY "UnitShift synthetic {name} source"')
        options=f'path "{source["path"]}"'
        if source['format']=='CSV': options+=", header 'true', delimiter ',', quote '\"', escape '\"'"
        else: options+=", multiLine 'true'"
        plan.append(f'CREATE LIGHTNING FILESTORE TABLE {source["table"]} FROM {source["database"]} FORMAT {source["format"]} OPTIONS ({options})')
    (ROOT/'data/zetaris-manifest.json').write_text(json.dumps(manifest,indent=2))
    (ROOT/'data/register-sources.sql').write_text(';\n\n'.join(plan)+';\n')
    if not args.apply:
        print('Prepared exports, manifest and SQL. Use --apply to upload and register the project sources.');return
    # Do not send the workstation's AWS credentials to Zetaris. Mint a temporary,
    # read-only session restricted to this one synthetic prefix.
    policy={'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['s3:GetObject'],'Resource':[f'arn:aws:s3:::{bucket}/unitshift/v1/*']},
        {'Effect':'Allow','Action':['s3:ListBucket'],'Resource':[f'arn:aws:s3:::{bucket}'],
         'Condition':{'StringLike':{'s3:prefix':['unitshift/v1','unitshift/v1/*']}}}]}
    session_path=ROOT/'.state/zetaris-s3-session.json'
    if session_path.exists():
        credentials=json.loads(session_path.read_text())
        from datetime import datetime, timezone, timedelta
        expiry=datetime.fromisoformat(credentials['Expiration'].replace('Z','+00:00'))
        if expiry<datetime.now(timezone.utc)+timedelta(hours=1): credentials=None
    else: credentials=None
    if credentials is None:
        session=json.loads(aws('sts','get-federation-token','--name','unitshift-s3-readonly',
                               '--duration-seconds','129600','--policy',json.dumps(policy),'--output','json'))
        credentials=session['Credentials']
        fd=os.open(session_path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as stream: json.dump(credentials,stream)
    manifest['session_expires_at']=credentials['Expiration']
    (ROOT/'data/zetaris-manifest.json').write_text(json.dumps(manifest,indent=2))
    print('S3 read-only session expires:',credentials['Expiration'],flush=True)
    private_plan=[]
    auth=', '+', '.join(f'{key} "{credentials[value]}"' for key,value in
                       [('awsAccessKeyId','AccessKeyId'),('awsSecretAccessKey','SecretAccessKey'),('awsSessionToken','SessionToken')])
    for statement in plan:
        private_plan.append(statement[:-1]+auth+')' if statement.startswith('CREATE LIGHTNING FILESTORE') else statement)
    # Fixed project prefix only; no public ACL and no synchronization deletion.
    for source in SOURCES.values():
        aws('s3','cp',str(folder/source['filename']),f's3://{bucket}/unitshift/v1/{source["filename"]}','--only-show-errors')
    existing=zetaris_query('SHOW LIGHTNING DATABASES')
    names={str(row[0]).upper() for row in existing.get('data',[])}
    for name,source in SOURCES.items():
        db=source['database']
        if db not in names:
            print('Registering',db,flush=True);zetaris_query(plan[list(SOURCES).index(name)*2])
        tables=zetaris_query(f'SHOW LIGHTNING TABLES {db}')
        table_names={str(row[0]).lower() for row in tables.get('data',[])}
        if source['table'].lower() in table_names:
            opts=private_plan[list(SOURCES).index(name)*2+1].split(' OPTIONS ',1)[1]
            zetaris_query(f'UPDATE LIGHTNING FILESTORE TABLE {source["table"]} FROM {db} OPTIONS '+opts)
            result=zetaris_query(f'SELECT * FROM {db}.{source["table"]} LIMIT 1')
            if result.get('headers')!=['case_id','record_json'] and set(result.get('headers',[]))!={'case_id','record_json'}:
                raise RuntimeError('Existing source has an unexpected schema; refusing to replace it.')
            print('Verified existing table',db+'.'+source['table'],flush=True)
        else:
            print('Creating project table',db+'.'+source['table'],flush=True)
            # Auth is sent only to the user's configured Zetaris endpoint, never to logs or source files.
            response=zetaris_query(private_plan[list(SOURCES).index(name)*2+1])
            print('Table registration completed.',flush=True)
        result=zetaris_query(f'SELECT * FROM {db}.{source["table"]} LIMIT 1')
        if not result.get('data'): raise RuntimeError('Registered source returned no rows.')
        count=zetaris_query(f'SELECT COUNT(*) FROM {db}.{source["table"]}')
        observed=int(count['data'][0][0])
        if observed!=manifest['expected_row_counts'][name]:
            raise RuntimeError(f'{db} source completeness failed: expected {manifest["expected_row_counts"][name]}, got {observed}.')
        print('Readback OK:',db+'.'+source['table'],flush=True)

if __name__=='__main__': main()
