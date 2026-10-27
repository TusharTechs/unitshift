CREATE OR REPLACE SCHEMASTORE VIEW retail_evidence WITH CONTAINER unitshift_control AS
SELECT CAST(l.source_row AS BIGINT) AS source_row,l.invoice_no,l.stock_code,l.description,
 CAST(l.quantity AS BIGINT) AS quantity,l.invoice_date,l.unit_price,l.customer_id,l.country,l.line_amount,
 CAST(l.credit_flag AS INT) AS credit_flag,CAST(l.exact_duplicate_of AS BIGINT) AS exact_duplicate_of,
 l.fx_date,f.gbp_per_eur,CAST(CAST(l.line_amount AS DECIMAL(24,8))/CAST(f.gbp_per_eur AS DECIMAL(18,8)) AS DECIMAL(24,8)) AS calculated_eur,
 CAST(p.description_variants AS INT) AS description_variants,CAST(i.line_count AS INT) AS invoice_line_count
FROM UNITSHIFT_RETAIL.lines l
LEFT JOIN UNITSHIFT_RETAIL.product_catalog p ON l.stock_code=p.stock_code
LEFT JOIN UNITSHIFT_RETAIL.invoice_summary i ON l.invoice_no=i.invoice_no
LEFT JOIN UNITSHIFT_ECB.gbp_eur f ON l.fx_date=f.rate_date;
