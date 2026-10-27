"""Create the project's semantic view over demand and verified stock."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.providers import zetaris_query
from app.config import ROOT

SQL='''CREATE OR REPLACE SCHEMASTORE VIEW customer_promises WITH CONTAINER unitshift_control AS
SELECT order_id, customer, sku, quantity, due_hours, unit_revenue_minor, available_units,
       GREATEST(LEAST(quantity, available_units -
         (SUM(quantity) OVER (PARTITION BY sku ORDER BY due_hours, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) - quantity)), 0) AS supported_units
FROM (
 SELECT get_json_object(d.record_json, '$.id') AS order_id,
        get_json_object(d.record_json, '$.customer') AS customer,
        get_json_object(d.record_json, '$.sku') AS sku,
        CAST(get_json_object(d.record_json, '$.quantity') AS BIGINT) AS quantity,
        CAST(get_json_object(d.record_json, '$.due_hours') AS BIGINT) AS due_hours,
        CAST(get_json_object(d.record_json, '$.unit_revenue_minor') AS BIGINT) AS unit_revenue_minor,
        CAST(get_json_object(i.record_json, '$.on_hand_units') AS BIGINT) +
        CAST(get_json_object(i.record_json, '$.verified_inbound_units') AS BIGINT) AS available_units
 FROM UNITSHIFT_DEMAND.customer_orders d
 JOIN UNITSHIFT_STOCK.inventory i ON get_json_object(d.record_json, '$.sku') = get_json_object(i.record_json, '$.sku')
 WHERE d.case_id = 'operations' AND i.case_id = 'operations'
) typed_source_evidence'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--create-container',action='store_true');args=p.parse_args()
    (ROOT/'data/operational-semantic-view.sql').write_text(SQL+';\n')
    if not args.apply: print('Prepared semantic-view SQL. Use --apply to register.');return
    if args.create_container: zetaris_query('CREATE SCHEMASTORE CONTAINER unitshift_control')
    zetaris_query(SQL)
    result=zetaris_query('SELECT * FROM unitshift_control.customer_promises ORDER BY order_id')
    if len(result.get('data',[]))!=6: raise RuntimeError('Semantic view did not return exactly six customer promises.')
    (ROOT/'data/operational-view.json').write_text(json.dumps({'name':'unitshift_control.customer_promises','verified_rows':6},indent=2))
    print(json.dumps(result),flush=True)

if __name__=='__main__': main()
