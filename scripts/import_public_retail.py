"""Reproducible UCI Online Retail + ECB historical reference-rate ingestion.
No business fields are invented. Derived totals, candidate links and FX values
are labelled transformations. Source identities remain anonymised as published.
"""
import argparse,csv,hashlib,json,sqlite3,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_HALF_UP
from bisect import bisect_right
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def xlsx_rows(archive):
    with zipfile.ZipFile(archive) as outer:
        name=next(n for n in outer.namelist() if n.endswith('.xlsx'))
        import io
        with zipfile.ZipFile(io.BytesIO(outer.read(name))) as book:
            strings=[]
            with book.open('xl/sharedStrings.xml') as stream:
                for _,e in ET.iterparse(stream,events=['end']):
                    if e.tag==NS+'si': strings.append(''.join(t.text or '' for t in e.iter(NS+'t')));e.clear()
            with book.open('xl/worksheets/sheet1.xml') as stream:
                for _,row in ET.iterparse(stream,events=['end']):
                    if row.tag!=NS+'row':continue
                    values=['']*8
                    for cell in row.findall(NS+'c'):
                        col=''.join(c for c in cell.attrib['r'] if c.isalpha());index=0
                        for c in col:index=index*26+ord(c)-64
                        if not 1<=index<=8:continue
                        v=cell.find(NS+'v');text=v.text if v is not None else ''
                        if cell.attrib.get('t')=='s':text=strings[int(text)]
                        elif cell.attrib.get('t')=='inlineStr':text=''.join(t.text or '' for t in cell.iter(NS+'t'))
                        values[index-1]=text or ''
                    yield int(row.attrib['r']),values
                    row.clear()

def pennies(value):return int((Decimal(str(value))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_csv(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--retail-zip',type=Path,required=True);ap.add_argument('--ecb-csv',type=Path,required=True);args=ap.parse_args()
    folder=ROOT/'.state/public';folder.mkdir(parents=True,exist_ok=True);public=ROOT/'data/public';public.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(folder/'retail.sqlite3');db.row_factory=sqlite3.Row
    db.executescript('DROP TABLE IF EXISTS lines; DROP TABLE IF EXISTS fx; CREATE TABLE lines(source_row INTEGER PRIMARY KEY,invoice_no TEXT,stock_code TEXT,description TEXT,quantity INTEGER,invoice_date TEXT,unit_price TEXT,customer_id TEXT,country TEXT,line_amount TEXT,credit_flag INTEGER,exact_duplicate_of INTEGER,fx_date TEXT);CREATE TABLE fx(rate_date TEXT PRIMARY KEY,gbp_per_eur TEXT);')
    fx=[]
    with args.ecb_csv.open(encoding='utf-8') as f:
        for r in csv.DictReader(f):fx.append({'rate_date':r['TIME_PERIOD'],'gbp_per_eur':r['OBS_VALUE']})
    fx.sort(key=lambda r:r['rate_date']);dates=[r['rate_date'] for r in fx]
    db.executemany('INSERT INTO fx VALUES (:rate_date,:gbp_per_eur)',fx)
    seen={};batch=[];count=0;positive=Decimal(0);negative=Decimal(0);signed=Decimal(0)
    monthly={};countries={};headers=None
    fields=['source_row','invoice_no','stock_code','description','quantity','invoice_date','unit_price','customer_id','country','line_amount','credit_flag','exact_duplicate_of','fx_date']
    with (folder/'retail_lines.csv').open('w',newline='',encoding='utf-8') as output:
        writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
        for rowno,v in xlsx_rows(args.retail_zip):
            if rowno==1:headers=v;continue
            if headers!=['InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice','CustomerID','Country']:raise ValueError('Unexpected source schema.')
            inv,sku,description,q,serial,price,customer,country=v
            seconds=int((Decimal(serial)*86400).quantize(Decimal('1'),rounding=ROUND_HALF_UP));when=datetime(1899,12,30)+timedelta(seconds=seconds)
            quantity=int(Decimal(q));price_decimal=Decimal(price);amount=price_decimal*quantity
            day=when.date().isoformat();pos=bisect_right(dates,day)-1
            if pos<0:raise ValueError('No preceding reference rate for '+day)
            fp=(inv,sku,description,quantity,when.isoformat(),str(price_decimal.normalize()),customer,country)
            duplicate=seen.get(fp,0);seen.setdefault(fp,rowno)
            record=dict(zip(fields,[rowno,inv,sku,description,quantity,when.isoformat(),str(price_decimal),customer,country,str(amount),int(inv.upper().startswith('C')),duplicate,dates[pos]]))
            writer.writerow(record);batch.append(tuple(record[k] for k in fields));count+=1
            signed+=amount
            if amount>0:positive+=amount
            if amount<0:negative+=amount
            month=day[:7];monthly.setdefault(month,{'month':month,'lines':0,'signed_amount_minor':0});monthly[month]['lines']+=1;monthly[month]['signed_amount_minor']+=pennies(amount)
            c=countries.setdefault(country,{'country':country,'lines':0,'signed_amount_minor':0});c['lines']+=1;c['signed_amount_minor']+=pennies(amount)
            if len(batch)>=3000:db.executemany('INSERT INTO lines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',batch);batch=[]
        if batch:db.executemany('INSERT INTO lines VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',batch)
    if count!=541909:raise ValueError('Source completeness: expected 541909 rows, got '+str(count))
    db.executescript('CREATE INDEX lines_invoice ON lines(invoice_no);CREATE INDEX lines_customer_sku ON lines(customer_id,stock_code,quantity);CREATE INDEX lines_duplicate ON lines(exact_duplicate_of);')
    db.commit()
    def rows(sql,args=()):return [dict(r) for r in db.execute(sql,args)]
    invoices=rows('SELECT invoice_no,MIN(invoice_date) first_recorded_at,MAX(invoice_date) last_recorded_at,COUNT(*) line_count,COUNT(DISTINCT CASE WHEN LENGTH(customer_id)>0 THEN customer_id END) customer_count,MAX(credit_flag) cancellation_flag FROM lines GROUP BY invoice_no ORDER BY invoice_no')
    products=rows('SELECT stock_code,COUNT(*) line_count,COUNT(DISTINCT CASE WHEN LENGTH(description)>0 THEN description END) description_variants,MIN(CASE WHEN LENGTH(description)>0 THEN description END) sample_description FROM lines GROUP BY stock_code ORDER BY stock_code')
    write_csv(folder/'invoice_summary.csv',invoices,list(invoices[0]));write_csv(folder/'product_catalog.csv',products,list(products[0]));write_csv(folder/'ecb_gbp_eur.csv',fx,['rate_date','gbp_per_eur'])
    cases=[]
    def add(kind,row,title,candidates=None,count_candidates=0):
        identity='uci-'+str(row['source_row']);amount=pennies(row['line_amount'])
        cases.append({'id':identity,'kind':kind,'title':title,'source_row':row['source_row'],'invoice_no':row['invoice_no'],'stock_code':row['stock_code'],'customer_id':row['customer_id'],'description':row['description'],'country':row['country'],'recorded_at':row['invoice_date'],'amount_minor':amount,'evidence':[row]+(candidates or []),'candidate_count':count_candidates,'warning':'Candidate matches are inferred from attributes. The source does not include an explicit original-invoice reference, refund approval, or payment settlement.' if kind=='cancellation' else 'A review signal is not proof of an error, fraud or financial loss.'})
    credits=rows('SELECT * FROM lines WHERE credit_flag=1 AND CAST(line_amount AS REAL)<0 ORDER BY ABS(CAST(line_amount AS REAL)) DESC,source_row LIMIT 24')
    for r in credits:
        candidates=[]
        if r['customer_id']:
            candidates=rows('SELECT * FROM lines WHERE credit_flag=0 AND customer_id=? AND stock_code=? AND quantity=? AND invoice_date<=? ORDER BY invoice_date DESC,source_row',(r['customer_id'],r['stock_code'],-r['quantity'],r['invoice_date']))
            candidates=[c for c in candidates if Decimal(c['unit_price'])==Decimal(r['unit_price'])]
        add('cancellation',r,'Trace a recorded cancellation',candidates[:8],len(candidates))
    for r in rows('SELECT * FROM lines WHERE exact_duplicate_of>0 ORDER BY ABS(CAST(line_amount AS REAL)) DESC,source_row LIMIT 8'):
        add('duplicate',r,'Inspect duplicate-looking rows',rows('SELECT * FROM lines WHERE source_row=?',(r['exact_duplicate_of'],)))
    for r in rows('SELECT * FROM lines WHERE LENGTH(customer_id)=0 AND CAST(line_amount AS REAL)>0 ORDER BY CAST(line_amount AS REAL) DESC,source_row LIMIT 5'):add('missing_identity',r,'Resolve missing customer identity')
    for r in rows('SELECT * FROM lines WHERE CAST(unit_price AS REAL)=0 AND quantity>0 ORDER BY quantity DESC,source_row LIMIT 3'):add('zero_price',r,'Inspect a zero-price transaction')
    coverage=rows('SELECT COUNT(DISTINCT invoice_no) invoices,COUNT(DISTINCT CASE WHEN LENGTH(customer_id)>0 THEN customer_id END) customers,COUNT(DISTINCT stock_code) products,COUNT(DISTINCT country) countries,SUM(CASE WHEN LENGTH(customer_id)=0 THEN 1 ELSE 0 END) missing_customer_lines,SUM(CASE WHEN exact_duplicate_of>0 THEN 1 ELSE 0 END) duplicate_looking_lines,SUM(credit_flag) cancellation_lines,MIN(invoice_date) first_recorded_at,MAX(invoice_date) last_recorded_at FROM lines')[0]
    manifest={'version':'uci-352-ecb-v1','historical':True,'synthetic':False,'currency':'GBP','source_timezone':'Unspecified by source; source calendar dates preserved.','downloaded_at':datetime.now(timezone.utc).isoformat(),'publishers':[
      {'id':'uci','name':'UCI Machine Learning Repository','title':'Online Retail','creator':'Daqing Chen','citation':'Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33.','url':'https://archive.ics.uci.edu/dataset/352/online+retail','download_url':'https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip','license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','archive_sha256':sha(args.retail_zip),'rows':count},
      {'id':'ecb','name':'European Central Bank','title':'GBP per EUR daily reference observations','url':'https://data-api.ecb.europa.eu/service/data/EXR/D.GBP.EUR.SP00.A?startPeriod=2010-11-25&endPeriod=2011-12-09&format=csvdata','license':'ECB statistics reuse policy; source acknowledged, observations unchanged.','license_url':'https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html','download_sha256':sha(args.ecb_csv),'rows':len(fx)}],
      'transformations':['All 541909 published transaction lines retained, including missing values and duplicate-looking lines.','Excel dates converted to source calendar timestamps; no timezone assumption.','Line amount is Quantity × UnitPrice using decimal arithmetic. Summary display rounded to GBP pennies; exact source price and calculated decimal amount retained.','Invoice and product tables are derived views of the same UCI export, not independent business systems.','Cancellation candidates match customer, stock code, opposite quantity, price and a non-future timestamp; no original-reference link is asserted.','FX reporting uses the same-or-prior calendar-date ECB observation, retaining its date and rate; this is retrospective reporting, not a point-in-time trading or settlement quote. EUR values are UnitShift calculations, not ECB-published transaction values.'],
      'exports':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.glob('*.csv')},'counts':coverage,'source_limits':['Historical records, not live business operations.','No supplier quotes, inventory balances, fulfillment promises, refund authorisations or measured customer savings are present.','No attempt to re-identify the anonymised customers or retailer.']}
    snapshot={'manifest':manifest,'stats':{**coverage,'lines':count,'gross_positive_minor':pennies(positive),'negative_lines_value_minor':pennies(negative),'signed_total_minor':pennies(signed),'monthly':list(monthly.values()),'countries':sorted(countries.values(),key=lambda r:r['lines'],reverse=True)},'cases':cases,'products':sorted(products,key=lambda r:r['line_count'],reverse=True)[:30],'generated_at':manifest['downloaded_at']}
    (public/'manifest.json').write_text(json.dumps(manifest,indent=2));(public/'snapshot.json').write_text(json.dumps(snapshot,indent=2))
    print(json.dumps({'counts':coverage,'lines':count,'cases':len(cases),'exports':manifest['exports']},indent=2));db.close()
if __name__=='__main__':main()
