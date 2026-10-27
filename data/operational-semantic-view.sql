CREATE OR REPLACE SCHEMASTORE VIEW customer_promises WITH CONTAINER unitshift_control AS
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
) typed_source_evidence;
