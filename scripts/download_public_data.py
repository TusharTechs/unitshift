"""Download only the attributed public sources, then run the source-preserving importer."""
import hashlib,subprocess,sys
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parent.parent
SOURCES=[('online-retail.zip','https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip','f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b'),('ecb-gbp-eur.csv','https://data-api.ecb.europa.eu/service/data/EXR/D.GBP.EUR.SP00.A?startPeriod=2010-11-25&endPeriod=2011-12-09&format=csvdata',None)]
def main():
 folder=ROOT/'.state/downloads';folder.mkdir(parents=True,exist_ok=True)
 print('Sources: UCI Online Retail (Daqing Chen, 2015), CC BY 4.0; ECB statistics, attributed reuse. Historical records only.',flush=True)
 for name,url,expected in SOURCES:
  destination=folder/name
  if not destination.exists():
   print('Downloading',name,flush=True)
   with urlopen(Request(url,headers={'User-Agent':'UnitShift-public-data/0.3'}),timeout=120) as response:
    raw=response.read(40_000_001)
   if len(raw)>40_000_000:raise ValueError('Unexpected source size; download was not imported.')
   if expected and hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('UCI source hash changed. Check the primary publisher before importing.')
   destination.write_bytes(raw)
  if expected and hashlib.sha256(destination.read_bytes()).hexdigest()!=expected:raise ValueError('Cached UCI source hash does not match the attributed release.')
 subprocess.run([sys.executable,str(ROOT/'scripts/import_public_retail.py'),'--retail-zip',str(folder/'online-retail.zip'),'--ecb-csv',str(folder/'ecb-gbp-eur.csv')],cwd=ROOT,check=True)
 print('Local historical browsing is ready. Live investigations require your own configured provider credentials.',flush=True)
if __name__=='__main__':main()
