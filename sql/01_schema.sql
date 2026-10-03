-- PostgreSQL database is created by docker-compose.yml.

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS staging.sales_validated (
    order_id       VARCHAR(7)    NOT NULL,
    order_date     DATE          NOT NULL,
    customer_id    VARCHAR(6)    NOT NULL,
    product_id     VARCHAR(4)    NOT NULL,
    quantity       SMALLINT      NOT NULL,
    unit_price     NUMERIC(12,2) NOT NULL,
    total_amount   NUMERIC(14,2) NOT NULL,
    source_file    VARCHAR(255)  NOT NULL,
    ingested_at    TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reference/master table for customers.
CREATE TABLE IF NOT EXISTS core.customers (
    customer_id VARCHAR(6) PRIMARY KEY,
    CONSTRAINT customers_id_format_ck
        CHECK (customer_id ~ '^C[0-9]{5}$')
);

-- Reference/master table for products.
CREATE TABLE IF NOT EXISTS core.products (
    product_id VARCHAR(4) PRIMARY KEY,
    CONSTRAINT products_id_format_ck
        CHECK (product_id ~ '^P[0-9]{3}$')
);

-- Trusted sales table: one row per order/product line.
CREATE TABLE IF NOT EXISTS core.sales (
    sale_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      VARCHAR(7)    NOT NULL,
    order_date    DATE          NOT NULL,
    customer_id   VARCHAR(6)    NOT NULL,
    product_id    VARCHAR(4)    NOT NULL,
    quantity      SMALLINT      NOT NULL,
    unit_price    NUMERIC(12,2) NOT NULL,
    total_amount  NUMERIC(14,2) NOT NULL,
    source_file   VARCHAR(255)  NOT NULL,
    loaded_at     TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT sales_order_id_format_ck
        CHECK (order_id ~ '^O[0-9]{6}$'),
    CONSTRAINT sales_customer_id_format_ck
        CHECK (customer_id ~ '^C[0-9]{5}$'),
    CONSTRAINT sales_product_id_format_ck
        CHECK (product_id ~ '^P[0-9]{3}$'),
    CONSTRAINT sales_quantity_ck
        CHECK (quantity BETWEEN 1 AND 100),
    CONSTRAINT sales_unit_price_ck
        CHECK (unit_price > 0 AND unit_price <= 100000),
    CONSTRAINT sales_total_amount_ck
        CHECK (total_amount = ROUND(quantity * unit_price, 2)),

    CONSTRAINT sales_customer_fk
        FOREIGN KEY (customer_id) REFERENCES core.customers(customer_id),
    CONSTRAINT sales_product_fk
        FOREIGN KEY (product_id) REFERENCES core.products(product_id),

    -- Business key: one product can appear only once per order in this model.
    CONSTRAINT sales_order_product_uk
        UNIQUE (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_sales_order_date
    ON core.sales (order_date);

CREATE INDEX IF NOT EXISTS idx_sales_customer_id
    ON core.sales (customer_id);

CREATE INDEX IF NOT EXISTS idx_sales_product_id
    ON core.sales (product_id);

COMMENT ON SCHEMA staging IS
    'Temporary/landing layer for validated batches before loading the trusted core layer.';

COMMENT ON SCHEMA core IS
    'Trusted relational layer used by downstream analytics and applications.';

COMMENT ON TABLE core.sales IS
    'One row per order/product sales line. The business key is (order_id, product_id).';
