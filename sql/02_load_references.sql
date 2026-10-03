-- Optional reference-data seed for a fresh PostgreSQL instance.
-- The Python loader performs the same operation with ON CONFLICT DO NOTHING,
-- so this file is primarily useful for inspecting or initializing the reference domains manually.

INSERT INTO core.customers (customer_id)
SELECT 'C' || LPAD(g::text, 5, '0')
FROM generate_series(1, 500) AS g
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO core.products (product_id)
SELECT 'P' || LPAD(g::text, 3, '0')
FROM generate_series(1, 50) AS g
ON CONFLICT (product_id) DO NOTHING;
