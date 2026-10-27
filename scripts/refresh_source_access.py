"""Renew only UnitShift source access using the judge EC2 instance's scoped role.
Credentials remain in memory and are sent only to the configured Zetaris API.
No workstation AWS identity or IAM user key is installed on the server.
"""
import hashlib,json,sys
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT
from app.providers import zetaris_query

def main():
 local=build_opener(ProxyHandler({}));base='http://169.254.169.254/latest/'
 token=local.open(Request(base+'api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'300'}),timeout=5).read().decode()
 def metadata(path):return local.open(Request(base+'meta-data/'+path,headers={'X-aws-ec2-metadata-token':token}),timeout=5).read().decode()
 role=metadata('iam/security-credentials/').strip()
 if role!='unitshift-judge-20261027-sources':raise RuntimeError('Unexpected instance role; refusing to transmit credentials.')
 credentials=json.loads(metadata('iam/security-credentials/'+role))
 fingerprint=hashlib.sha256(credentials['AccessKeyId'].encode()).hexdigest();cache=ROOT/'.state/source-access-status.json'
 if cache.exists() and json.loads(cache.read_text()).get('key_fingerprint')==fingerprint:
  print('Scoped source session remains current.');return
 sources=list(json.loads((ROOT/'data/zetaris-manifest.json').read_text())['sources'].values())
 public=json.loads((ROOT/'data/public/zetaris.json').read_text())['sources']
 sources += [{**v,'format':'CSV'} for v in public.values()]
 auth=', '+', '.join(f'{k} "{credentials[v]}"' for k,v in [('awsAccessKeyId','AccessKeyId'),('awsSecretAccessKey','SecretAccessKey'),('awsSessionToken','Token')])
 for s in sources:
  path=s.get('path','')
  if '/unitshift/v1/' not in path:raise RuntimeError('Source path is outside the project prefix.')
  opts=f'path "{path}"'
  if s['format']=='CSV':opts+=", header 'true', delimiter ',', quote '\"', escape '\"', multiLine 'true'"
  else:opts+=", multiLine 'true'"
  zetaris_query(f"UPDATE LIGHTNING FILESTORE TABLE {s['table']} FROM {s['database']} OPTIONS ("+opts+auth+')')
 cache.write_text(json.dumps({'key_fingerprint':fingerprint,'expires_at':credentials['Expiration'],'source_tables':len(sources)}));cache.chmod(0o600)
 print('Refreshed',len(sources),'own-prefix source registrations. Expiration:',credentials['Expiration'])
if __name__=='__main__':main()
