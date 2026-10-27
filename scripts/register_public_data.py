"""Register licensed public exports and an actual cross-publisher semantic view."""
import argparse,json,sys,subprocess,uuid,os,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT
from app.providers import zetaris_query
from app.receipts import load_receipts
SOURCES={
 'lines':{'database':'UNITSHIFT_RETAIL','table':'lines','filename':'retail_lines.csv','count':541909},
 'invoices':{'database':'UNITSHIFT_RETAIL','table':'invoice_summary','filename':'invoice_summary.csv','count':25900},
 'products':{'database':'UNITSHIFT_RETAIL','table':'product_catalog','filename':'product_catalog.csv','count':4070},
 'fx':{'database':'UNITSHIFT_ECB','table':'gbp_eur','filename':'ecb_gbp_eur.csv','count':None}}
VIEW="""CREATE OR REPLACE SCHEMASTORE VIEW retail_evidence WITH CONTAINER unitshift_control AS
SELECT CAST(l.source_row AS BIGINT) AS source_row,l.invoice_no,l.stock_code,l.description,
 CAST(l.quantity AS BIGINT) AS quantity,l.invoice_date,l.unit_price,l.customer_id,l.country,l.line_amount,
 CAST(l.credit_flag AS INT) AS credit_flag,CAST(l.exact_duplicate_of AS BIGINT) AS exact_duplicate_of,
 l.fx_date,f.gbp_per_eur,CAST(CAST(l.line_amount AS DECIMAL(24,8))/CAST(f.gbp_per_eur AS DECIMAL(18,8)) AS DECIMAL(24,8)) AS calculated_eur,
 CAST(p.description_variants AS INT) AS description_variants,CAST(i.line_count AS INT) AS invoice_line_count
FROM UNITSHIFT_RETAIL.lines l
LEFT JOIN UNITSHIFT_RETAIL.product_catalog p ON l.stock_code=p.stock_code
LEFT JOIN UNITSHIFT_RETAIL.invoice_summary i ON l.invoice_no=i.invoice_no
LEFT JOIN UNITSHIFT_ECB.gbp_eur f ON l.fx_date=f.rate_date"""
def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--bucket',default=os.environ.get('UNITSHIFT_S3_BUCKET'));p.add_argument('--region',default=os.environ.get('UNITSHIFT_S3_REGION','us-west-1'));p.add_argument('--profile');p.add_argument('--credentials-file',type=Path);p.add_argument('--create-container',action='store_true');args=p.parse_args()
 if not args.bucket or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',args.bucket):p.error('Set --bucket to your own S3 bucket, or configure UNITSHIFT_S3_BUCKET.')
 manifest=json.loads((ROOT/'data/public/manifest.json').read_text());bucket=args.bucket
 sources={k:dict(v) for k,v in SOURCES.items()};sources['fx']['count']=manifest['publishers'][1]['rows']
 plan=[]
 for source in sources.values():
  source['path']=f"s3a://{bucket}/unitshift/v1/public/{source['filename']}"
  source['options']=f"(path \"{source['path']}\", header 'true', delimiter ',', quote '\"', escape '\"', multiLine 'true')"
  plan.append(f"CREATE LIGHTNING FILESTORE TABLE {source['table']} FROM {source['database']} FORMAT CSV OPTIONS {source['options']}")
 (ROOT/'data/public/semantic-view.sql').write_text(VIEW+';\n')
 (ROOT/'data/public/register-sources.sql').write_text(';\n'.join(plan)+';\n')
 if not args.apply:print('Prepared four public source registrations and the semantic join.');return
 aws=['aws']+(['--profile',args.profile] if args.profile else [])
 credentials=json.loads(args.credentials_file.read_text()) if args.credentials_file else json.loads(subprocess.run(aws+['configure','export-credentials','--format','process'],check=True,capture_output=True,text=True).stdout)
 credentials['SessionToken']=credentials.get('SessionToken') or credentials.get('Token')
 if not credentials.get('SessionToken') or not credentials.get('Expiration'):raise RuntimeError('Use temporary, read-only source credentials from a scoped AWS role. Long-lived IAM user credentials are not registered.')
 from datetime import datetime,timezone
 if datetime.fromisoformat(credentials['Expiration'].replace('Z','+00:00'))<=datetime.now(timezone.utc):raise RuntimeError('Refresh scoped source session first.')
 if args.create_container:zetaris_query('CREATE SCHEMASTORE CONTAINER unitshift_control')
 auth=', '+', '.join(f'{key} "{credentials[value]}"' for key,value in [('awsAccessKeyId','AccessKeyId'),('awsSecretAccessKey','SecretAccessKey'),('awsSessionToken','SessionToken')])
 rid=uuid.uuid4().hex;dbs={str(r[0]).upper() for r in zetaris_query('SHOW LIGHTNING DATABASES')['data']}
 for key,source in sources.items():
  subprocess.run(aws+['s3','cp',str(ROOT/'.state/public'/source['filename']),f"s3://{bucket}/unitshift/v1/public/{source['filename']}",'--region',args.region,'--only-show-errors'],check=True)
  if source['database'] not in dbs:
   zetaris_query(f"CREATE LIGHTNING DATABASE {source['database']} DESCRIBE BY \"UnitShift attributed public data\"");dbs.add(source['database'])
  tables={str(r[0]).lower() for r in zetaris_query('SHOW LIGHTNING TABLES '+source['database'])['data']}
  opts=source['options'][:-1]+auth+')'
  sql=(f"UPDATE LIGHTNING FILESTORE TABLE {source['table']} FROM {source['database']} OPTIONS {opts}" if source['table'] in tables else f"CREATE LIGHTNING FILESTORE TABLE {source['table']} FROM {source['database']} FORMAT CSV OPTIONS {opts}")
  zetaris_query(sql) # Credential-bearing options are never written to a receipt.
  count=zetaris_query(f"SELECT COUNT(*) AS row_count FROM {source['database']}.{source['table']}",rid)
  observed=int(count['data'][0][0])
  if observed!=source['count']:raise RuntimeError(f'Unexpected row count for {key}: {observed}')
  print('Verified',source['database']+'.'+source['table'],observed,flush=True)
 zetaris_query(VIEW,rid)
 sample=zetaris_query('SELECT * FROM unitshift_control.retail_evidence WHERE source_row IN (540423,540424) ORDER BY source_row',rid)
 if len(sample['data'])!=2:raise RuntimeError('Expected two real demonstration rows from semantic join.')
 joined=zetaris_query('SELECT COUNT(*) AS row_count FROM unitshift_control.retail_evidence',rid)
 if int(joined['data'][0][0])!=541909:raise RuntimeError('Semantic join multiplied or dropped source rows.')
 (ROOT/'data/public/zetaris.json').write_text(json.dumps({'run_id':rid,'sources':{k:{a:b for a,b in v.items() if a!='options'} for k,v in sources.items()},'semantic_view':'unitshift_control.retail_evidence','verified_join_rows':541909,'sample':sample,'receipts':load_receipts(rid),'source_session_expires_at':credentials['Expiration']},indent=2))
 print('Verified actual cross-publisher semantic view over 541909 rows.',flush=True)
if __name__=='__main__':main()
