CREATE LIGHTNING DATABASE UNITSHIFT_PURCHASE DESCRIBE BY "UnitShift synthetic purchase_orders source";

CREATE LIGHTNING FILESTORE TABLE orders FROM UNITSHIFT_PURCHASE FORMAT CSV OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/purchase_orders.csv", header 'true', delimiter ',', quote '"', escape '"');

CREATE LIGHTNING DATABASE UNITSHIFT_INVOICE DESCRIBE BY "UnitShift synthetic invoices source";

CREATE LIGHTNING FILESTORE TABLE invoice_lines FROM UNITSHIFT_INVOICE FORMAT JSON OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/invoices.json", multiLine 'true');

CREATE LIGHTNING DATABASE UNITSHIFT_RECEIVING DESCRIBE BY "UnitShift synthetic receiving source";

CREATE LIGHTNING FILESTORE TABLE receipts FROM UNITSHIFT_RECEIVING FORMAT JSON OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/receiving.json", multiLine 'true');

CREATE LIGHTNING DATABASE UNITSHIFT_DEMAND DESCRIBE BY "UnitShift synthetic customer_orders source";

CREATE LIGHTNING FILESTORE TABLE customer_orders FROM UNITSHIFT_DEMAND FORMAT CSV OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/customer_orders.csv", header 'true', delimiter ',', quote '"', escape '"');

CREATE LIGHTNING DATABASE UNITSHIFT_STOCK DESCRIBE BY "UnitShift synthetic inventory source";

CREATE LIGHTNING FILESTORE TABLE inventory FROM UNITSHIFT_STOCK FORMAT JSON OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/inventory.json", multiLine 'true');

CREATE LIGHTNING DATABASE UNITSHIFT_MARKET DESCRIBE BY "UnitShift synthetic supplier_offers source";

CREATE LIGHTNING FILESTORE TABLE supplier_offers FROM UNITSHIFT_MARKET FORMAT JSON OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/supplier_offers.json", multiLine 'true');

CREATE LIGHTNING DATABASE UNITSHIFT_POLICY DESCRIBE BY "UnitShift synthetic operating_policy source";

CREATE LIGHTNING FILESTORE TABLE operating_policy FROM UNITSHIFT_POLICY FORMAT JSON OPTIONS (path "s3a://zetaris-unitshift-hackathon-aws--workspaces3bucket-j7n3qhpnvcrf/unitshift/v1/operating_policy.json", multiLine 'true');
